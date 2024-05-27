import asyncio
import concurrent.futures
import datetime
import json
import os
from base64 import b64decode
from collections import defaultdict
import cv2
from confluent_kafka import Consumer
from deepface import DeepFace
from fastapi import FastAPI
from mtcnn import MTCNN

consumer = Consumer(
    {
        'bootstrap.servers': '10.80.161.74:9094',
        'group.id': 'foo',
        'receive.message.max.bytes': 10000000000,
    }
)
consumer.subscribe(['video-masking-topic'])

# producer = Producer({'bootstrap.servers': '10.80.163.35:8080', 'group.id': 'foo'})

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

    global_id_dict = defaultdict(int)
    recent_frames = []
    s3_url_dict = defaultdict(str)
    global_id = 0

    with concurrent.futures.ThreadPoolExecutor() as executor:
        face_locations_list = list(executor.map(recognize_face, images))
    create_folder(f'./images/{filename}')
    for i, face_locations in enumerate(face_locations_list):
        frame_cropped_paths = []
        for j, face_location in enumerate(face_locations):
            x, y, width, height = face_location
            cropped = images[i][y:y + height, x:x + width]  # Crop the face
            cropped_path = f'./images/{filename}/{i}:{j}.png'
            frame_cropped_paths.append(cropped_path)
            cv2.imwrite(cropped_path, cropped)
            s3_url_dict[cropped_path] = upload_s3.upload_file_to_s3(cropped_path)
            images[i][y:y + height, x:x + width] = 0  # Black out the face

            found = False
            for frame in recent_frames:
                for prev_cropped_path in frame:
                    is_same = compare_image(cropped_path, prev_cropped_path)
                    if is_same:
                        global_id_dict[cropped_path] = global_id_dict[prev_cropped_path]
                        found = True
                        break
                if found:
                    break

            if not found:
                global_id_dict[cropped_path] = global_id
                global_id += 1

        recent_frames.append(frame_cropped_paths)

        # 최근 10프레임만 유지
        if len(recent_frames) > 10:
            recent_frames.pop(0)

    images_into_video(images, f'./video/{filename.split(".")[0]}.mp4', fps=fps)

    return {
        "videoName": filename,
        "createdDate": datetime.datetime.now().isoformat(),
        "frameLength": len(images),
        "fps": fps,
        "resolution": {
            "width": video_width,
            "height": video_height
        },
        "frame": [{
            'frameId': frame_idx,
            'objects': [{
                'objectId': object_idx,
                'globalId': global_id_dict[f'./images/{filename}/{frame_idx}:{object_idx}.png'],
                'topLeftX': face_location[0],
                'topLeftY': face_location[1],
                'width': face_location[2],
                'height': face_location[3],
                'storagePath': s3_url_dict[f'./images/{file.filename}/{frame_idx}:{object_idx}.png']
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
    try:
        return DeepFace.verify(
            img1_path=f1_path,
            img2_path=f2_path,
            detector_backend='skip',
            model_name='Dlib',
            enforce_detection=False
        )['verified']
    except:
        return False


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
