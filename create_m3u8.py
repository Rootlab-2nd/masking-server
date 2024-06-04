import subprocess


def convert_to_hls(input_video_path, output_directory_path, filename, segment_time=10):
    output_m3u8_path = f"{output_directory_path}{filename}.m3u8"
    command = [
        'ffmpeg',
        '-i', input_video_path,
        '-hls_time', str(segment_time),
        '-hls_list_size', '0',
        '-hls_segment_filename', f'{output_directory_path}{filename}%d.ts',
        output_m3u8_path
    ]

    subprocess.run(command, check=True)
    return output_directory_path + filename + '.m3u8'
