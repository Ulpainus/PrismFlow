"""This package contains modules related to objective functions, optimizations, and network architectures."""
import importlib

# 【已修复】将绝对导入 'from models.base_model' 修改为相对导入 'from .base_model'
# 前面的点 '.' 告诉Python在当前目录（models/）下查找 base_model.py
from .base_model import BaseModel


def find_model_using_name(model_name):
    """Import the module "models/[model_name]_model.py"."""
    # 【已修复】确保模块路径相对于我们新的包结构是正确的
    model_filename = "cyclegan_lib.models." + model_name + "_model"
    modellib = importlib.import_module(model_filename)
    model = None
    target_model_name = model_name.replace('_', '') + 'model'
    for name, cls in modellib.__dict__.items():
        if name.lower() == target_model_name.lower() \
           and issubclass(cls, BaseModel):
            model = cls

    if model is None:
        print("In %s.py, there should be a subclass of BaseModel with class name that matches %s in lowercase." % (model_filename, target_model_name))
        exit(0)

    return model


def get_option_setter(model_name):
    """Return the static method <modify_commandline_options> of the model class."""
    model_class = find_model_using_name(model_name)
    return model_class.modify_commandline_options


def create_model(opt):
    """Create a model given the option."""
    model = find_model_using_name(opt.model)
    instance = model(opt)
    print("model [%s] was created" % type(instance).__name__)
    return instance
