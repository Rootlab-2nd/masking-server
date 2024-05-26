import upload_m3u8
import upload_s3
import create_m3u8

file_path = "C://Users//user//Desktop//GitRocket.png"



output_directory = "C://Users//user//Desktop//Cipher//hls_data"
input_video = "C://Users//user//Desktop//잡동사니//나락퀴즈쇼_오프닝.mp4"

m3u8_path = create_m3u8.convert_to_hls(input_video, output_directory)
print(m3u8_path)

s3_url = upload_m3u8.upload_m3u8(m3u8_path)
print("S3 URL:", s3_url)

