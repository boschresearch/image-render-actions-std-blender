
import enum

class EFileFormat(str, enum):
    JPEG = "JPEG"
    PNG = "PNG"
    OPEN_EXR = "OPEN_EXR"
# endclass

class EPixelType(str, enum):
    BW = "BW"
    RGB = "RGB"
    RGBA = "RGBA"
# endclass

class EColorDepth(str, enum):
    BITS8 = "8"
    BITS16 = "16"
    BITS32 = "32"
# endclass

class EOpenExrCodec(str, enum):
    ZIP = "ZIP"
# endclass

class CFileFormat:
    def __init__(self, _eFileFormat: EFileFormat):
        self.eFileFormat = _eFileFormat
    # enddef

    def GetDict(self) -> dict:
        return {
            "sFileFormat": self.eFileFormat
        }
    # enddef
# endclass

class CFileFormatJpeg(CFileFormat):
    def __init__(self, _ePixelType: EPixelType, _iQuality: int):
        super().__init__(EFileFormat.JPEG)
        self.ePixelType = _ePixelType
        self.iQuality = _iQuality
    # enddef

    def GetDict(self) -> dict:
        return {
            "sFileFormat": self.eFileFormat, 
            "sPixelType": self.ePixelType, 
            "sColorDepth": "8",
            "iQuality": self.iQuality,
        }
    # enddef
# endclass

class CFileFormatPng(CFileFormat):
    def __init__(self, _ePixelType: EPixelType, _eColorDepth: EColorDepth, _iCompression: int,):
        super.__init(EFileFormat.PNG)
        self.ePixelType = _ePixelType
        self.eColorDepth = _eColorDepth
        self.iCompression = _iCompression
    # enddef

    def GetDict(self) -> dict:
        return {
            "sFileFormat": self.eFileFormat, 
            "sPixelType": self.ePixelType, 
            "sColorDepth": self.eColorDepth,
            "iCompression": self.iCompression,
        }
    # enddef
# endclass

class CFileFormatOpenExr(CFileFormat):
    def __init__(self, _ePixelType: EPixelType, _eColorDepth: EColorDepth):
        super.__init(EFileFormat.OPEN_EXR)
        self.ePixelType = _ePixelType
        self.eColorDepth = _eColorDepth
        self.eCodec = EOpenExrCodec.ZIP
    # enddef

    def GetDict(self) -> dict:
        return {
            "sFileFormat": self.eFileFormat, 
            "sCodec": self.eCodec,
            "sPixelType": self.ePixelType, 
            "sColorDepth": self.eColorDepth,
        }
    # enddef
# endclass

class EFileOutputContentType(str, enum):
    IMAGE = "image"
    DEPTH = "depth"
# endclass

class CFileOutput:
    def __init__(self, _sOutput: str, _sFolder: str, _eContentType: EFileOutputContentType, _xFormat: CFileFormat):
        self.sOutput = _sOutput
        self.sFolder = _sFolder
        self.eContentType = _eContentType
        self.xFormat = _xFormat
    # enddef

    def GetDict(self) -> dict:
        return {
            "sOutput": self.sOutput,
            "sFolder": self.sFolder,
            "sContentType": self.eContentType,
            "mFormat": self.xFormat.GetDict(),
        }
# endclass


class CDefine:
    def __init__(self, _lFileOut: list[CFileOutput], _sId: str = "${filebasename}"):
        self.sDti = "/catharsys/blender/compositor:1"
        self.sId = _sId
        self.lFileOut = _lFileOut
    # enddef

    def GetDict(self) -> dict:
        return {
            "sDTI": self.sDti,
            "sId": self.sId,
            "lFileOut": [x.GetDict() for x in self.lFileOut],
        }
    # enddef
# endclass
