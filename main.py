import threading
# from pathlib import Path
# import os

#
# ffmpeg_dll_dir = Path(r"C:\Program Files (x86)\ffmpeg\bin")
# assert ffmpeg_dll_dir.exists(), ffmpeg_dll_dir
# os.add_dll_directory(str(ffmpeg_dll_dir))

if __name__ == '__main__':
    import LocalAgentApi, faulthandler
    from InputManager import InputManager

    faulthandler.enable()

    server_thread = threading.Thread(target=LocalAgentApi.start_api, daemon=True)
    server_thread.start()

    manager = InputManager()
    manager.start()