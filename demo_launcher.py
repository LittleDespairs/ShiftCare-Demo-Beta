import os
import sys


os.environ["SCHEDULE_APP_DEMO_MODE"] = "1"
os.environ["SHIFTCARE_DEMO"] = "1"

import launcher


if __name__ == "__main__":
    sys.exit(launcher.main())
