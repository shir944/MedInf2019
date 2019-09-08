from builtins import int
import io
import copy
import numpy as np

xrange = range

def read_pgm(pgmfile, img_buffer=None):
    """Read a greyscale image from a .pgm file

    :param pgmfile: An open file object
    :param img_buffer: Optional buffer to store image data
    :return:  A 2-tuple containing the pgm header comments and 2-d image data

    """
    # Read magic number and make sure it's correct for PGM format
    magic_num = pgmfile.readline().strip()
    if not magic_num:
        raise EOFError
    if magic_num != b'P5':
        raise IOError('Incorrect PGM header')

    # Read header fields into dictionary
    header_fields = dict()
    while pgmfile.peek(1)[:1] == b'#':
        line = pgmfile.readline().strip()
        try:
            field, content = line[1:].decode('ascii').split(' ', 1)
        except AttributeError:
            field, content = line[1:].split(' ', 1)

        header_fields[field] = content.split()

    # Extract frame dimensions
    dims = pgmfile.readline().strip()
    xdim, ydim = [int(s) for s in dims.split()]

    # Read max grey value
    max_val = int(pgmfile.read(4).strip())

    # Read frame data
    if img_buffer is None:
        image = pgmfile.read(xdim * ydim)
        img_data = np.fromstring(image, dtype=np.uint8).reshape(ydim, xdim)
    else:
        pgmfile.readinto(img_buffer)
        img_data = img_buffer

    return header_fields, img_data


def timestamp_usecs(frame_header):
    """Helper function to extract timestamp in microseconds from frame header

    :param frame_header: Header fields dictionary returned by read_pgm function
    :return: The frame timestamp in microseconds

    """
    secs, usecs = frame_header['time'][:2]
    return int(secs + usecs.zfill(6))


class PGMReader(object):

    """Read from a file containing a sequence of PGM images

    """

    def __init__(self, filepath):
        super(PGMReader, self).__init__()

        # Open PGM file for reading
        self.pgmfile = io.open(filepath, mode='rb')

        # Read first frame to determine video properties
        header_fields, img_data = read_pgm(self.pgmfile)
        self.index0 = int(header_fields['frame_ind'][0])
        self.time0 = timestamp_usecs(header_fields)
        self.frame0 = {'position': 0,
                       'index': 0,
                       'true_index': 0,
                       'timestamp': 0,
                       'data': img_data}

        # Allocate buffer to store image data
        self.img_buffer = np.zeros_like(self.frame0['data'], dtype=np.uint8)

        # Iterate over all frames collecting further information
        indices = []
        timestamps = []
        self.positions = []
        for frame in self:
            indices.append(frame['true_index'])
            timestamps.append(frame['timestamp'])
            self.positions.append(frame['position'])

        self.rewind()

        # Set read-only properties
        self._filepath = filepath
        self._fps = 1.0 / (np.nanmean(np.diff(timestamps)) * 1e-6)
        self._height, self._width = self.frame0['data'].shape
        self._length = len(indices)
        self._true_length = indices[-1] + 1

    def __del__(self):
        """Close the file when the reader is destroyed.
        
        """
        self.pgmfile.close()

    def __getitem__(self, key):
        """Allows us to access copies of video frames like an array with [] operator
        
        """
        if isinstance(key, slice):
            return [copy.deepcopy(self.seek_frame(idx)) for idx in xrange(*key.indices(len(self)))]
        else:
            return copy.deepcopy(self.seek_frame(key))

    def __len__(self):
        """Allows use of len() function to get number of frames
        
        """
        return self._length

    def __iter__(self):
        """Allows us to use the reader as an iterator
        
        """
        self.rewind()
        return self

    def next(self):
        """Required for an object implementing __iter__ to return the next item in the sequence
        
        """
        try:
            return self.next_frame()
        except EOFError:
            raise StopIteration

    __next__ = next  # Python 3 compatibility

    @property
    def filepath(self):
        """Path to the .pgm video file

        """
        return self._filepath

    @property
    def fps(self):
        """Average framerate of video in frames per second

        """
        return self._fps

    @property
    def width(self):
        """Width of video in pixels

        """
        return self._width

    @property
    def height(self):
        """Height of video in pixels

        """
        return self._height

    @property
    def length(self):
        """Number of frames present in video file

        """
        return self._length

    @property
    def true_length(self):
        """Number of frames, taking missing frames into account

        """
        return self._true_length

    def rewind(self):
        """Rewind to the first frame
         
        """
        self.pgmfile.seek(0)
        self.frame_ind = 0

    def seek_frame(self, n):
        """Seek to the position of the nth frame and read it
         
        """
        # Bounds checking
        if (n >= self.length) | (n < -self.length):
            raise IndexError

        # Wrap around for negative indices
        if n < 0:
            n += self.length

        # Seek to the position of the nth frame
        self.pgmfile.seek(self.positions[n])
        self.frame_ind = n

        return self.next_frame()

    def next_frame(self):
        """Read the frame at the current file position
          
        """
        # Remember file position
        pos = self.pgmfile.tell()

        # Read the next frame
        header_fields, data = read_pgm(self.pgmfile, self.img_buffer)

        frame = {'position': pos,
                 'index': self.frame_ind,
                 'true_index': int(header_fields['frame_ind'][0]) - self.index0,
                 'timestamp': timestamp_usecs(header_fields) - self.time0,
                 'data': data}

        self.frame_ind += 1

        return frame
