""" Download full spherical imagery from Google Street View.
"""
import json
import math
from io import BytesIO

import requests
from PIL import Image
from tqdm import tqdm


def get_concat_h(im1, im2):
    dst = Image.new('RGB', (im1.width + im2.width, im1.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    return dst

def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (0, im1.height))
    return dst

class StreetView:
    def __init__(self, latitude: float, longitude: float, zoom_factor: 4):
        """ Initialize StreetView class.
        
        Args:
            latitude (float):  streetview latitude
            longitude (float):  streetview longitude

        kwargs:
            zoom_factor (int):  zoom factor (1-4)
        """
        self.latitude = latitude
        self.longitude = longitude
        self._num_columns = 0
        self._num_rows = 0
        self._metadata = None
        self._meta_url = None
        assert zoom_factor < 6 and zoom_factor > 0
        self.zoom_factor = zoom_factor
    
    @property
    def meta_url(self):
        if not isinstance(self._meta_url, str):
            self._meta_url = "https://maps.google.com/cbk?output=json&hl=x-local&ll={},{}&cb_client=maps_sv&v=3".format(self.latitude, self.longitude)
        print(self._meta_url)
        return self._meta_url
    
    @property
    def metadata(self):
        if not isinstance(self._metadata, dict):
            resp = requests.get(self.meta_url)
            self._metadata = json.loads(resp.content)
        return self._metadata

    @property
    def original_height(self):
        return int(self.metadata['Data']['image_height'])
    
    @property
    def original_width(self):
        return int(self.metadata['Data']['image_width'])

    @property
    def pano_id(self):
        return self.metadata['Links'][0]['panoId']
    
    @property
    def output_width(self):
        return int(self.original_width / (2 ** (5 - self.zoom_factor)))
    
    @property
    def output_height(self):
        return int(self.original_height / (2 ** (5 - self.zoom_factor)))
    
    @property
    def num_rows(self):
        if self.zoom_factor == 2:
            return  int(math.ceil(self.output_height / 512)) + 1
        return int(math.ceil(self.output_height / 512))
    
    @property
    def num_columns(self):
        return int(math.ceil(self.output_width / 512))
    
    def download(self, output_path: str, output_type: str = 'png'):
        """ Downloads all tiles and saves individual tiles to a dictionary.
        
        Args:
            output_path (str):  path to save file
            output_type (str):  output filetype.  Default = 'png'
        """
        IMAGE = None
        cur_slice = None
        total_tiles = self.num_rows * self.num_columns

        with tqdm(total=total_tiles) as pbar:
            for row in range(self.num_rows):
                if cur_slice != None:
                    if IMAGE == None:
                        IMAGE = cur_slice
                    else:
                        IMAGE = get_concat_v(IMAGE, cur_slice)
                        
                    cur_slice = None
                for column in range(self.num_columns):
                    url = "https://cbks2.google.com/cbk?cb_client=maps_sv.tactile&authuser=%200&hl=en&panoid={}&output=tile&zoom={}&x={}&y={}".format(self.pano_id, self.zoom_factor, column, row)

                    resp = requests.get(url)
                    content = resp.content

                    if cur_slice == None:
                        cur_slice = Image.open(BytesIO(content))
                    else:
                        append_slice = Image.open(BytesIO(content))
                        cur_slice = get_concat_h(cur_slice, append_slice)
                    pbar.update()
            if IMAGE == None:
                IMAGE = cur_slice
        
        print("Saving image to {}".format(output_path))
        IMAGE.save(output_path, format=output_type)
        print("Image saved!")
                
if __name__ == "__main__":
    latitude = 40.0405135
    longitude = -75.426155
    
    sv = StreetView(latitude, longitude, zoom_factor=4)
    
    print(sv.num_rows)
    print(sv.num_columns)
    
    sv.download(output_path = "output_image.png")