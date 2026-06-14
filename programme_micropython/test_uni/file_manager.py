import time
import os
import json

'''
Sauvegarde les photos dans la machine e. image_<comptage>.jpg
ajouter '_' après un mot, le chiffre du fichier et le format
'''
class FileManager:
    def __init__(self, file_manager_name='filemanager.log'):
        self.FILE_MANAGER_LOG_NAME = file_manager_name
        self.last_request_filename = None
        self.suffix = None
        self.file_dict = {}

        try:
            # Check if the filename already exists in the storage
            # On vérifie si le nom est deja présent dans le stockage
            with open(self.FILE_MANAGER_LOG_NAME, 'r') as f:
                self.file_dict = json.loads(f.read())
        except Exception:
            # On s'assure que le fichier est bien présent
            if self.FILE_MANAGER_LOG_NAME not in os.listdir('.'):
                with open(self.FILE_MANAGER_LOG_NAME, 'w') as f:
                    f.write(json.dumps(self.file_dict))

    def new_jpg_fn(self, requested_filename=None):
        return (self.new_filename(requested_filename) + '.jpg')

    def new_filename(self, requested_filename):
        count = 0
        self.last_request_filename = requested_filename

        if requested_filename is None and self.last_request_filename is None:
            raise Exception('Please enter a filename for the first use of the function')

        if requested_filename in self.file_dict:
            count = self.file_dict[requested_filename] + 1
        self.file_dict[requested_filename] = count

        self.save_manager_file()
        new_filename = f"{requested_filename}_{count}" if count > 0 else f"{requested_filename}"

        return new_filename

    def save_manager_file(self):
        # Sauvegarde la nouvelle liste dans le stockage
        with open(self.FILE_MANAGER_LOG_NAME, 'w') as f:
            f.write(json.dumps(self.file_dict))


class Camera:
    """
    Mock Camera Class for standard Python testing.
    Simulates the behavior of the SPI Arducam without requiring actual hardware.
    """
    debug_information = False
    
    # Constants retained for compatibility with scripts that might import them
    CAM_REG_SENSOR_RESET = 0x07
    CAM_SENSOR_RESET_ENABLE = 0x40
    CAM_REG_SENSOR_ID = 0x40
    SENSOR_5MP_1 = 0x81
    SENSOR_3MP_1 = 0x82
    CAM_REG_COLOR_EFFECT_CONTROL = 0x27
    SPECIAL_NORMAL = 0x00
    CAM_REG_BRIGHTNESS_CONTROL = 0X22
    BRIGHTNESS_PLUS_4 = 7
    CAM_REG_CONTRAST_CONTROL = 0X23
    CONTRAST_MINUS_3 = 6
    CAM_REG_WB_MODE_CONTROL = 0X26
    WB_MODE_AUTO = 0
    
    # Resolution settings
    RESOLUTION_320X240 = 0X01
    RESOLUTION_640X480 = 0X02
    RESOLUTION_1600X1200 = 0X06
    
    valid_3mp_resolutions = {
        '320x240': RESOLUTION_320X240, 
        '640x480': RESOLUTION_640X480, 
        '1600x1200': RESOLUTION_1600X1200,
    }
    valid_5mp_resolutions = valid_3mp_resolutions

    BUFFER_MAX_LENGTH = 255
    WHITE_BALANCE_WAIT_TIME_MS = 500

    def __init__(self, spi_bus=None, cs=None, skip_sleep=False, debug_text_enabled=False):
        # We ignore spi_bus and cs in the mock
        self.debug_text_enabled = debug_text_enabled
        self.camera_idx = '5MP' # Mocking a 5MP camera
        
        self.run_start_up_config = True
        self.current_pixel_format = 0x01 # JPG
        self.old_pixel_format = self.current_pixel_format

        self.current_resolution_setting = self.RESOLUTION_640X480
        self.old_resolution = self.current_resolution_setting

        self.received_length = 0
        self.total_length = 0

        self.start_time = int(time.time() * 1000)
        
        if debug_text_enabled:
            print(f'[MOCK CAMERA] Initialized. Version = {self.camera_idx}')

    def capture_jpg(self):
        """Simulates capturing a JPG."""
        if self.debug_text_enabled: 
            print('[MOCK CAMERA] Entered capture_jpg')
            
        self.run_start_up_config = False
        
        # Simulate an image payload size
        self.received_length = 1024 * 50 # Simulate a 50KB image
        self.total_length = self.received_length
        
        if self.debug_text_enabled: 
            print('[MOCK CAMERA] Finished capture_jpg. Image buffered.')

    def _update_progress(self, progress, bar_length=20):
        filled_length = int(bar_length * progress)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        print("Progress: |{}| {}%".format(bar, int(progress * 100)), end='\r')

    def saveJPG(self, filename="image.jpg", progress_bar=True): 
        """
        Simulates saving the JPG by writing a dummy file to the disk.
        """
        if self.debug_text_enabled:
            print(f'[MOCK CAMERA] Attempting to save to {filename}')
            
        with open(filename, 'wb') as f:
            # We write a tiny valid 1-pixel gray JPG just so the file is real and can be opened
            # This is a base64 decoded minimal JPG
            minimal_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x15\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf2\xef\xff\xd9'
            f.write(minimal_jpg)
            
        if progress_bar: 
            self._update_progress(1)
            print()
            
        print("[MOCK CAMERA] Image saved")

    @property
    def resolution(self):
        return self.current_resolution_setting
        
    @resolution.setter
    def resolution(self, new_resolution):
        input_string_lower = new_resolution.lower()        
        if input_string_lower in self.valid_5mp_resolutions:
            self.current_resolution_setting = self.valid_5mp_resolutions[input_string_lower]
        else:
            raise ValueError(f"Invalid resolution provided. Please select from {list(self.valid_5mp_resolutions.keys())}")

    # Mocked setter functions that simply pass
    def set_pixel_format(self, new_pixel_format): pass
    def set_brightness_level(self, brightness): pass
    def set_filter(self, effect): pass
    def set_saturation_control(self, saturation_value): pass
    def set_contrast(self, contrast): pass
    def set_white_balance(self, environment): pass


# =====================================================================
# BLOC DE TEST AUTONOME
# =====================================================================
if __name__ == "__main__":
    print("--- Testing FileManager ---")
    fm = FileManager()
    filename = fm.new_jpg_fn("test_flight")
    print(f"Generated filename: {filename}")
    
    print("\n--- Testing Mock Camera ---")
    # In standard Python, we don't pass real SPI/Pin objects
    cam = Camera(debug_text_enabled=True)
    
    print("\nSetting Resolution...")
    cam.resolution = "1600X1200"
    cam.set_brightness_level(cam.BRIGHTNESS_PLUS_4)
    cam.set_contrast(cam.CONTRAST_MINUS_3)
    
    print("\nCapturing Image...")
    cam.capture_jpg()
    
    print("\nSaving Image...")
    cam.saveJPG(filename)
    
    print(f"\nTest complete. Check your directory for '{filename}'.")