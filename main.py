from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, Response
from confluent_kafka import Consumer
import asyncio
import json
import cv2
from mtcnn import MTCNN
import os
import time
import datetime
import concurrent.futures
import dotenv
import boto3

consumer = Consumer({'bootstrap.servers': '', 'group.id': ''})
consumer.subscribe([''])

app = FastAPI()

client_s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("CREDENTIALS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("CREDENTIALS_SECRET_KEY")
)


async def consume_messages():
    current_loop = asyncio.get_running_loop()
    print("start consuming...")
    while True:
        message = await current_loop.run_in_executor(None, consumer.poll, 1.0)
        if message is None:
            continue
        if message.error():
            print(f"Kafka Consumer error: {message.error()}")
            continue
        user_data = json.loads(message.value())
        user = User(**user_data)
        await save_user(user)


@app.get("/metadata")
async def get_metadata():
    return {''}


@app.post('/video')
async def upload_video(file: UploadFile):
    content = await file.read()
    with open(os.path.join('./video', file.filename), 'wb') as fp:
        fp.write(content)
    return Response(status_code=200)


@app.post('/videofff')
async def download_masked_video(file: UploadFile):
    start = time.time()
    content = await file.read()
    with open(os.path.join('./video', file.filename), 'wb') as fp:
        fp.write(content)

    images, fps = video_into_images(f'./video/{file.filename}')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        face_locations_list = list(executor.map(recognize_face, images))

    for i, face_locations in enumerate(face_locations_list):
        for j, face_location in enumerate(face_locations):
            x, y, width, height = face_location
            cropped = images[i][y:y + height, x:x + width]  # Crop the face
            cv2.imwrite(f'./images/{i}:{j}.png', cropped)
            images[i][y:y + height, x:x + width] = 0  # Black out the face

    images_into_video(images, f'./video/{file.filename.split(".")[0]}.mp4', fps=fps)

    end = time.time()

    sec = (end - start)
    result = datetime.timedelta(seconds=sec)
    print(result)

    return FileResponse(f'./video/{file.filename.split(".")[0]}.mp4')


def video_into_images(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = 1
    images = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        images.append(frame)
        count += 1
    cap.release()
    return images, fps


def images_into_video(images, filename, fps):
    height, width, layers = images[0].shape
    size = (width, height)
    out = cv2.VideoWriter(filename=filename, fourcc=cv2.VideoWriter.fourcc('M', 'P', '4', 'V'), fps=fps, frameSize=size)

    for image in images:
        out.write(image)

    out.release()


def recognize_face(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    detector = MTCNN()
    face_locations = [face_location['box'] for face_location in detector.detect_faces(image)]
    return face_locations

