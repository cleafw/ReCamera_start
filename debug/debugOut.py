import logging
import os
import sys

import colorlog
from logging.handlers import RotatingFileHandler
from datetime import datetime


from data.path import logSavePath

# 使用系统logging输出-----------------------------------------------------------------------------------------------------
# 设置日志的配置信息
# handler = logging.StreamHandler(stream=Sys.stdout)
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
#
# # # 输出不同级别的日志信息
# # logging.debug('这是一个 debug 级别的日志信息')
# # logging.info('这是一个 info 级别的日志信息')
# # logging.warning('这是一个 warning 级别的日志信息')
# # logging.error('这是一个 error 级别的日志信息')
# # logging.critical('这是一个 critical 级别的日志信息')
# -----------------------------------------------------------------------------------------------------
# 使用自定义log输出-----------------------------------------------------------------------------------------------------
# 本日志文件py模块的根目录（path文件中设置）
# cur_path = os.path.dirname(os.path.realpath(__file__))      # 当前项目路径
# log_path = os.path.join(os.path.dirname(cur_path), 'logs')  # log_path为存放日志的路径
log_colors_config = {
    'DEBUG': 'white',
    'INFO': 'cyan',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}
# default_formats = {
#     'color_format': '%(log_color)s%(asctime)s-%(name)s-%(filename)s-[line:%(lineno)d]-%(levelname)s-[日志信息]: %(message)s',
#     'log_format': '%(asctime)s-%(name)s-%(filename)s-[line:%(lineno)d]-%(levelname)s-[日志信息]: %(message)s'
# }
default_formats = {
    'color_format': '%(log_color)s%(asctime)s-%(levelname)s-[日志信息]: %(message)s',
    'log_format': '%(asctime)s-%(levelname)s-[日志信息]: %(message)s'
}

class HandleLog:
    """
    先创建日志记录器（logging.getLogger），然后再设置日志级别（logger.setLevel），
    接着再创建日志文件，也就是日志保存的地方（logging.FileHandler），然后再设置日志格式（logging.Formatter），
    最后再将日志处理程序记录到记录器（addHandler）
    """
    debug_level_save = False    # 是否保存debug级别的日志
    error_level_save = False     # 是否保存error级别的日志

    def __init__(self):
        log_path = logSavePath
        if not os.path.exists(log_path):
            os.mkdir(log_path)  # 若不存在logs文件夹，则自动创建
        self.__now_time = datetime.now().strftime('%Y-%m-%d')  # 当前日期格式化
        self.__all_log_path = os.path.join(log_path, self.__now_time + "-all" + ".log")  # 收集所有日志信息文件 的名称
        self.__error_log_path = os.path.join(log_path, self.__now_time + "-error" + ".log")  # 收集错误日志信息文件 的名称
        self.__logger = logging.getLogger(__name__)  # 使用唯一的logger名字
        self.__logger.setLevel(logging.DEBUG)  # 设置默认日志记录器记录级别------------------------------

    @staticmethod
    def __init_logger_handler(log_path):
        """
        创建日志记录器handler，用于收集日志
        :param log_path: 日志文件路径
        :return: 日志记录器
        """
        logger_handler = RotatingFileHandler(filename=log_path, maxBytes=1 * 1024 * 1024, backupCount=3, encoding='utf-8')  # 写入文件，如果文件超过1M大小时，切割日志文件，仅保留3个文件
        return logger_handler

    @staticmethod
    def __init_console_handle():
        """
        创建终端日志记录器handler，用于输出到控制台
        :return: 终端日志记录器
        """
        console_handle = colorlog.StreamHandler()  # 创建终端日志记录器
        return console_handle

    def __set_log_handler(self, logger_handler, level=logging.DEBUG):
        """
        设置handler级别并添加到logger收集器
        :param logger_handler: 日志记录器
        :param level: 日志记录器级别
        """
        logger_handler.setLevel(level=level)  # 设置日志记录器级别
        self.__logger.addHandler(logger_handler)  # 添加日志记录器到logger收集器

    def __set_color_handle(self, console_handle):
        """
        设置handler级别并添加到终端logger收集器
        :param console_handle: 终端日志记录器
        """
        console_handle.setLevel(logging.DEBUG)  # 设置终端日志记录器级别
        self.__logger.addHandler(console_handle)  # 添加终端日志记录器到logger收集器

    @staticmethod
    def __set_color_formatter(console_handle, color_config):
        """
        设置输出格式-控制台
        :param console_handle: 终端日志记录器
        :param color_config: 控制台打印颜色配置信息
        """
        formatter = colorlog.ColoredFormatter(default_formats["color_format"], log_colors=color_config)  # 设置控制台日志格式
        console_handle.setFormatter(formatter)  # 应用格式到控制台日志记录器

    @staticmethod
    def __set_log_formatter(file_handler):
        """
        设置日志输出格式-日志文件
        :param file_handler: 日志记录器
        """
        formatter = logging.Formatter(default_formats["log_format"], datefmt='%a, %d %b %Y %H:%M:%S')  # 设置日志文件格式
        file_handler.setFormatter(formatter)  # 应用格式到日志文件记录器

    @staticmethod
    def __close_handler(file_handler):
        """
        关闭handler
        :param file_handler: 日志记录器
        """
        file_handler.close()  # 关闭日志记录器

    def __console(self, level, message):
        """
        构造日志收集器
        :param level: 日志级别
        :param message: 日志信息
        """
        all_logger_handler = self.__init_logger_handler(self.__all_log_path)  # 创建日志文件
        error_logger_handler = self.__init_logger_handler(self.__error_log_path)  # 创建错误日志文件
        console_handle = self.__init_console_handle()  # 创建终端日志记录器

        self.__set_log_formatter(all_logger_handler)  # 设置日志格式
        self.__set_log_formatter(error_logger_handler)  # 设置错误日志格式
        self.__set_color_formatter(console_handle, log_colors_config)  # 设置控制台日志格式

        if self.debug_level_save:
            self.__set_log_handler(all_logger_handler)  # 设置handler级别并添加到logger收集器
        if self.error_level_save:
            self.__set_log_handler(all_logger_handler, level=logging.ERROR)  # 设置错误日志handler级别并添加到logger收集器
        self.__set_color_handle(console_handle)  # 设置控制台handler并添加到logger收集器

        if level == 'info':
            self.__logger.info(message)  # 记录info级别日志
        elif level == 'debug':
            self.__logger.debug(message)  # 记录debug级别日志
        elif level == 'warning':
            self.__logger.warning(message)  # 记录warning级别日志
        elif level == 'error':
            self.__logger.error(message)  # 记录error级别日志
        elif level == 'critical':
            self.__logger.critical(message)  # 记录critical级别日志

        # 避免日志输出重复问题
        self.__logger.removeHandler(all_logger_handler)
        self.__logger.removeHandler(error_logger_handler)
        self.__logger.removeHandler(console_handle)

        self.__close_handler(all_logger_handler)  # 关闭日志记录器
        self.__close_handler(error_logger_handler)  # 关闭错误日志记录器

    # 多参数消息转化为一个字符串消息

    def debug(self, message, *args):
        formatted_message = message + ' '.join(map(str, args))
        self.__console('debug', formatted_message)  # 调用debug日志

    def info(self, message, *args):
        formatted_message = message + ' '.join(map(str, args))
        self.__console('info', formatted_message)  # 调用info日志

    def warning(self, message, *args):
        formatted_message = message + ' '.join(map(str, args))
        self.__console('warning', formatted_message)  # 调用warning日志

    def error(self, message, *args):
        formatted_message = message + ' '.join(map(str, args))
        self.__console('error', formatted_message)  # 调用error日志

    def critical(self, message, *args):
        formatted_message = message + ' '.join(map(str, args))
        self.__console('critical', formatted_message)  # 调用critical日志

log = HandleLog()  # 自定义的 logging 模块

# -----------------------------------------------------------------------------------------------------
# log.info("这是日志信息")
# log.debug("这是debug信息")
# log.warning("这是警告信息")
# log.error("这是错误日志信息")
# log.critical("这是严重级别信息")
# logging.debug('这是一个 debug 级别的日志信息')
# logging.info('这是一个 info 级别的日志信息')
# logging.warning('这是一个 warning 级别的日志信息')
# logging.error('这是一个 error 级别的日志信息')
# logging.critical('这是一个 critical 级别的日志信息')

# 输出字典信息内容

# 输出字典内容
def printDict(my_dict: dict):
    for key, value in my_dict.items():
        print(f"{key}: {value}\n")

# 输出实例对象的所有属性和值
def printObjectAttributes(obj):
    """
    输出实例对象的所有属性和值
    """
    # 获取对象的属性字典
    attributes = vars(obj)

    # 遍历属性字典并打印每个属性名和值
    for key, value in attributes.items():
        print(f"{key}: {value}\n")

# 输出带时间的调试信息 ms
def debug_print_ms(message):
    # 获取当前时间，并格式化到毫秒（截取 microsecond 前3位）
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"{now} - DEBUG - {message}")

# 输出带时间的调试信息 us
def debug_print_us(message):
    # 直接格式化输出微秒（6位）
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    print(f"{now} - DEBUG - {message}")

# # 假设已经配置了log
# log = logging.getLogger(__name__)

