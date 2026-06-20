import os


def delete():
    directory_path = "targetDir/"
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        print(file_path)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            # elif os.path.isdir(file_path):
            #     print(f"{file_path} はディレクトリであるため、削除されませんでした。")
        except Exception as e:
            print(f"{e} while deleting {file_path}")
