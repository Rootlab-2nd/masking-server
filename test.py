import upload_m3u8
import upload_s3
import create_m3u8


# s3_url = upload_s3.upload_file_to_s3(f'./images/KakaoTalk_Video_2024-05-25-17-16-36.mp4/0:0.png')
# print("S3 URL:", s3_url)
create_m3u8.convert_to_hls('res/video/건록이.mp4', 'res/video/', '건록이')

