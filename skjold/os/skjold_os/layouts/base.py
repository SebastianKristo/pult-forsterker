"""Grensesnittet en layout må oppfylle. app.Ui bygger en ViewModel (dict) og kaller render()."""
from ..gfx import Canvas


class Layout:
    W, H = 160, 128
    SS = 3          # supersampling
    name = "base"

    def canvas(self): return Canvas(self.W, self.H, self.SS)

    def render(self, vm):
        """vm['screen'] ∈ boot, welcome, reboot, switch, play, pair, menu, clock, offline, off.
        Returnerer et PIL-bilde i W×H."""
        c = self.canvas()
        getattr(self, "draw_" + vm["screen"], self.draw_off)(c, vm)
        if vm.get("vol_overlay") and vm["screen"] in ("play", "switch", "offline"):
            self.draw_volume(c, vm)
        return c.frame()

    def draw_off(self, c, vm): c.clear()
