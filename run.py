import warnings
import sys
from loguru import logger
from PyQt5.QtWidgets import QApplication
from app.main import MangaOCRApp 

warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.module")
warnings.filterwarnings("ignore", category=UserWarning, module="accelerate")

logger.remove()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    main_window = MangaOCRApp()
    main_window.show()
    sys.exit(app.exec_())