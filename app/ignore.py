import warnings
from loguru import logger

def ignore_warnings():
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.module")
    warnings.filterwarnings("ignore", category=UserWarning, module="accelerate")

    logger.remove()