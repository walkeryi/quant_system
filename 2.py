import sys
import traceback
import matplotlib.pyplot as plt
import numpy as np
# ========== 新增：中文显示配置 ==========
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用系统自带的“黑体”显示中文
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方块的问题

def check_python_version():
    """检测Python版本（matplotlib对Python有最低版本要求）"""
    print("===== 1. 检测Python版本 =====")
    py_version = sys.version_info
    version_str = f"{py_version.major}.{py_version.minor}.{py_version.micro}"
    print(f"当前Python版本：{version_str}")

    # matplotlib 3.7+ 要求Python 3.8+
    if py_version >= (3, 8):
        print("✅ Python版本符合matplotlib要求（≥3.8）")
    else:
        print("⚠️ Python版本过低（<3.8），可能导致matplotlib安装/运行异常")
    print()


def check_matplotlib_install():
    """检测matplotlib是否安装、版本及核心模块可用性"""
    print("===== 2. 检测matplotlib安装状态 =====")
    try:
        # 导入核心模块
        import matplotlib
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure

        # 输出版本信息
        print(f"matplotlib版本：{matplotlib.__version__}")
        print("✅ 成功导入matplotlib核心模块：")
        print("   - matplotlib (主库)")
        print("   - matplotlib.pyplot (pyplot模块)")
        print("   - matplotlib.figure.Figure (Figure类)")

        # 检测依赖（numpy是matplotlib的核心依赖）
        try:
            import numpy
            print(f"✅ 依赖库numpy已安装，版本：{numpy.__version__}")
        except ImportError:
            print("❌ 缺失核心依赖：numpy（matplotlib运行必需）")

    except ImportError as e:
        print("❌ matplotlib安装异常/未找到，错误信息：")
        print(f"   {str(e)}")
        print("\n💡 修复建议：执行以下命令重装matplotlib：")
        print(f"   python -m pip install matplotlib -U -i https://pypi.tuna.tsinghua.edu.cn/simple")
    except Exception as e:
        print("❌ 导入matplotlib时发生未知错误：")
        traceback.print_exc()
    print()


def test_matplotlib_plot():
    """测试matplotlib是否能正常绘图（核心功能验证）"""
    print("===== 3. 测试matplotlib绘图功能 =====")
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        # 创建简单图形
        fig, ax = plt.subplots(figsize=(5, 3))
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        ax.plot(x, y, label='sin(x)')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title('测试图：sin曲线')
        ax.legend()

        # 尝试显示图形（非交互式环境会自动跳过阻塞）
        print("✅ 成功创建绘图对象，即将显示测试图...")
        plt.show(block=False)  # block=False避免卡住，5秒后自动关闭
        plt.pause(5)  # 显示5秒
        plt.close(fig)  # 关闭图形

        print("✅ 绘图功能测试通过！")

    except Exception as e:
        print("❌ 绘图功能测试失败，错误信息：")
        traceback.print_exc()
        print("\n💡 可能原因：")
        print("   1. 缺少图形后端（如Tkinter），可安装：pip install tkinter")
        print("   2. 服务器/无桌面环境，可设置无界面后端：")
        print("      import matplotlib; matplotlib.use('Agg')")
    print()


def check_interpreter_path():
    """检测当前运行的Python解释器路径（排查环境不匹配问题）"""
    print("===== 4. 检测Python解释器路径 =====")
    interpreter_path = sys.executable
    print(f"当前运行的Python解释器：{interpreter_path}")
    print("\n💡 重要提示：")
    print(f"   请确保你的IDE（PyCharm/VSCode）使用的Python解释器路径与上面一致！")
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("      matplotlib环境/依赖检测工具")
    print("=" * 50)
    print()

    # 依次执行检测
    check_python_version()
    check_matplotlib_install()
    check_interpreter_path()
    test_matplotlib_plot()

    print("=" * 50)
    print("检测完成！")
    print("👉 若所有检测项均为✅，说明环境配置正确；")
    print("👉 若有❌/⚠️，请根据提示修复后重新运行本脚本。")