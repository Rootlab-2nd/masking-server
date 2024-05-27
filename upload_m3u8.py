import os

import upload_s3


def upload_m3u8(m3u8_path):
    with open(m3u8_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    updated_lines = []
    for line in lines:
        line = line.strip()
        if line.endswith('.ts'):
            print(line)
            ts_file_path = os.path.join(os.path.dirname(m3u8_path), line)
            s3_url = upload_s3.upload_file_to_s3(ts_file_path)
            s3_url = s3_url.split('/')[-1]
            print(s3_url)
            updated_lines.append(s3_url)
        else:
            updated_lines.append(line)

    with open(m3u8_path, 'w', encoding='utf-8') as file:
        file.write("\n".join(updated_lines))

    s3_url = upload_s3.upload_file_to_s3(m3u8_path)
    return s3_url

