from .. import compositor

class CImage:
    def __init__(self, _xCompositor: compositor.CDefine, _sId: str = "${filebasename}"):
        self.sDti = "/catharsys/blender/render/output/image:1"
        self.sId = _sId
        self.xCompositor = _xCompositor
    # enddef

    def GetDict(self) -> dict:
        return {
            "sDTI": self.sDti,
            "sId": self._sId,
            "mCompositor": self.xCompositor.GetDict(),
        }
    # enddef
# endclass

