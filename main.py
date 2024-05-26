from fastapi import FastAPI, UploadFile, File
from confluent_kafka import Consumer, Producer
from base64 import b64decode
import asyncio
import json
import cv2
from mtcnn import MTCNN
from deepface import DeepFace
import os
import datetime
import concurrent.futures
import dotenv
import boto3

consumer = Consumer(
    {
        'bootstrap.servers': '192.168.2.220:9094',
        'group.id': 'foo',
        'receive.message.max.bytes': 2013486160,
    }
)
consumer.subscribe(['video-masking-topic'])

# producer = Producer({'bootstrap.servers': '10.80.163.35:8080', 'group.id': 'foo'})

# client_s3 = boto3.client(
#     's3',
#     aws_access_key_id=os.getenv("CREDENTIALS_ACCESS_KEY"),
#     aws_secret_access_key=os.getenv("CREDENTIALS_SECRET_KEY")
# )

app = FastAPI()


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

        file = json.loads(message.value())
        video_file = file['videoFile']

        filename = video_file['originalName']
        video = video_file['bytes']

        bytes2mp4(video, filename)

        metadata = mask_video(filename)
        print(metadata)


@app.on_event("startup")
async def startup_event():
    await asyncio.create_task(consume_messages())


@app.on_event("shutdown")
async def shutdown_event():
    consumer.close()


def bytes2mp4(file: bytearray, filename: str):
    with open(os.path.join('./video', filename), 'wb') as fp:
        fp.write(b64decode(file))


def mask_video(filename):
    images, fps, video_width, video_height = video_into_images(f'./video/{filename}')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        face_locations_list = list(executor.map(recognize_face, images))
    crop_img_idx = 0
    create_folder(f'./images/{filename}')
    for i, face_locations in enumerate(face_locations_list):
        for j, face_location in enumerate(face_locations):
            x, y, width, height = face_location
            cropped = images[i][y:y + height, x:x + width]  # Crop the face
            cv2.imwrite(f'./images/{filename}/{i}:{j}.png', cropped)
            images[i][y:y + height, x:x + width] = 0  # Black out the face
            crop_img_idx += 1

    images_into_video(images, f'./video/{filename.split(".")[0]}.mp4', fps=fps)

    return {
        "videoName": filename,
        "createdDate": datetime.datetime.now().isoformat(),
        "frameLength": len(images),
        "fps": round(fps),
        "resolution": {
            "width": video_width,
            "height": video_height
        },
        "frame": [{
            'frameId': frame_idx,
            'objects': [{
                'objectId': object_idx,
                'topLeftX': face_location[0],
                'topLeftY': face_location[1],
                'width': face_location[2],
                'height': face_location[3],
            }
                for object_idx, face_location in enumerate(face_locations_list[frame_idx])
            ]
        }
            for frame_idx, image in enumerate(images)
        ]
    }


def video_into_images(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    count = 1
    images = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        images.append(frame)
        count += 1
    cap.release()
    return images, fps, width, height


def images_into_video(images, filename, fps):
    height, width, layers = images[0].shape
    size = (width, height)
    out = cv2.VideoWriter(filename=filename, fourcc=cv2.VideoWriter.fourcc('m', 'p', '4', 'v'), fps=fps, frameSize=size)

    for image in images:
        out.write(image)

    out.release()


def compare_image(
        f1_path: str,
        f2_path: str
):
    return DeepFace.verify(img1_path=f1_path, img2_path=f2_path, detector_backend='ssd', model_name='VGG-Face')[
        'verified']


def recognize_face(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    detector = MTCNN()
    face_locations = [face_location['box'] for face_location in detector.detect_faces(image)]
    return face_locations


def create_folder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print('Error: Creating directory. ' + directory)
