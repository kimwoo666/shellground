"""Developer wrapper: the builder, not the study page, owns this VM."""
import json
from conda_teaching.engine import CondaEngine
from conda_teaching.setup_diagnostics import check_setup_ui as check_native_ui
from conda_teaching.setup_smoke import ROOT,setup_fingerprint


def check_setup_ui(channel):
    class BorrowedEngine(CondaEngine):
        def close(self):
            if self.bridge:self.bridge.close()
            self.bridge=None
            # The surrounding build_runtime context, not this study page,
            # retains ownership of channel/VM and guarantees final shutdown.
    engine=BorrowedEngine();engine.channel=channel
    report=check_native_ui(engine,ROOT/'ui-previews')
    report.update(fingerprint=setup_fingerprint(),
        scope='Linux source Qt + builder-owned actual guest; not frozen packaging')
    (ROOT/'.conda-build/setup-ui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
