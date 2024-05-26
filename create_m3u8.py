import subprocess

def convert_to_hls(input_video_path, output_directory, segment_time=10):
    output_m3u8_path = f"{output_directory}/output.m3u8"
    command = [
        'ffmpeg',
        '-i', input_video_path,
        '-codec','copy',
        '-start_number', '0',
        '-hls_time', str(segment_time),
        '-hls_list_size', '0',
        '-f', 'hls',
        output_m3u8_path
    ]

    subprocess.run(command, check=True)
    return output_m3u8_path

