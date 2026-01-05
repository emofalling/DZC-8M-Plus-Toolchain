import re
import os, sys

# typing
import enum
from typing import Optional, TypeAlias, Generic, TypeVar

import argparse

__version__ = "0.1.0"

rematch_singleline_comments = re.compile(r'(\".*?\"|\'.*?\')|(//[^\n]*|#[^\n]*)')
rematch_multiline_comments = re.compile(r'/\*(?:[^*]|\*(?!/))*\*/', flags=re.DOTALL)

def remove_comments_preserve_lines(code):
    """
    移除代码中的注释，但保留行号信息。删除多行注释时，会用等数量的换行符替代，从而保留行号。
    
    参数:
        code: 源代码字符串
        
    返回:
        处理后的代码字符串，注释被移除但行号保留
    """
    
    # 第一步：处理多行注释 /* */
    # 使用非贪婪匹配来匹配多行注释
    # (?:[^*]|\*(?!/))* 匹配非*字符，或者*后面不跟/的情况
    
    def replace_multiline(match):
        """替换多行注释为等行数的空行"""
        comment = match.group(0)
        # 计算注释中的行数
        lines_in_comment = comment.count('\n')
        # 返回相应数量的换行符（保留行数）
        return '\n' * lines_in_comment
    
    # 使用 DOTALL 标志让 . 匹配换行符
    code = re.sub(rematch_multiline_comments, replace_multiline, code)
    
    # 第二步：处理单行注释 # 和 //
    
    def replace_single_line(match):
        """替换单行注释"""
        # 如果匹配到的是字符串内容（第一组），则保留原样
        if match.group(1):
            return match.group(1)
        # 否则是注释，替换为空
        else:
            return ''
    
    # 逐行处理，保留行号
    result_lines = []
    for line in code.split('\n'):
        # 移除该行中的单行注释
        line_clean = re.sub(rematch_singleline_comments, replace_single_line, line)
        result_lines.append(line_clean)
    
    return '\n'.join(result_lines)

"""
寄存器:
[0] PC  程序计数器 总是指向下一条指令。修改它可以实现跳转。
[1] AF  ALU符号位。当调用ADD/ADDC/SUB/SUBC/NEG/CMP指令时, ALU符号会被设置。可写。
[2] SP  栈指针, 为后来的子程序调用做准备。当前作为通用寄存器，但建议用于子程序中的父地址保存。
[3] GIO 通信寄存器, 用于与外部设备通信。
[4] R0  通用寄存器
[5] R1  通用寄存器
[6] R2  通用寄存器
[7] R3  通用寄存器
"""

"""
PAUSE: [0000xxxx]
NOP:   [0001xxxx]
MOVZ:  [00100R][VV]
MOVLZ: [00101R][C(8)][Vxxxx]
MOVN:  [00110R][VV]
MOVLN: [00111R][C(8)][Vxxxx]
ADD:   [0100xR][VV]
SUB:   [0101xR][VV]
ADDC:  [0110xR][VV]
SUBB:  [0111xR][VV]
INC:   [10000R]
DEC:   [10001R]
CMP:   [1001xXXX][VV]
NOT:   [1010xR][Vxxxx]
AND:   [1011xR][VV]
OR:    [1100xR][VV]
XOR:   [1101xR][VV]
SHL:   [1110xR][VV]
SHR:   [1111xR][VV]
"""

class RegisterEnum(enum.Enum):
    PC = 0b000
    AF = 0b001
    SP = 0b010
    GIO = 0b011
    R0 = 0b100
    R1 = 0b101
    R2 = 0b110
    R3 = 0b111

class OpEnum(enum.Enum):
    PAUSE = 0b00000000
    NOP   = 0b00010000
    MOVZ  = 0b00100000
    MOVLZ = 0b00101000
    MOVN  = 0b00110000
    MOVLN = 0b00111000
    ADD   = 0b01000000
    SUB   = 0b01010000
    ADDC  = 0b01100000
    SUBB  = 0b01110000
    INC   = 0b10000000
    DEC   = 0b10001000
    CMP   = 0b10010000
    NOT   = 0b10100000
    AND   = 0b10110000
    OR    = 0b11000000
    XOR   = 0b11010000
    SHL   = 0b11100000
    SHR   = 0b11110000

class Arg:
    name = "_"
    """Generel Argument, Not use directly."""
    def __init__(self, value: int, repr: str):
        self.value = value
        self.repr = repr
    def parse_bin(self) -> int:
        """
        :return: 解析后的二进制值
        :rtype: int
        """
        return self.value
    def get_literal(self) -> str:
        """
        :return: 用于信息提示的字面量
        :rtype: str
        """
        return self.repr

class ArgOverflowException(Exception):
    pass

class ConstArg(Arg):
    name = "常量"
    def __init__(self, value: int | str, repr: str, flag_table: Optional[dict[str, int]] = None):
        """
        :param value: 常量值。str表示标记引用
        :type value: int | str
        :param repr: 原字面量
        :type repr: str
        :param flag_table: 标记表，用于解析标记引用。若value的类型为str，则必须提供此参数
        :type flag_table: Optional[dict[str, int]]
        """
        self._value = value
        if isinstance(value, str):
            value = -1
        super().__init__(value, repr)
        self.flag_table = flag_table
    @property
    def value(self) -> int:
        if isinstance(self._value, int):
            return self._value
        if self.flag_table is None:
            raise ArgOverflowException(f"无法解析标记引用，没有提供标记表: {self._value}")
        addr = self.flag_table.get(self._value)
        if addr is not None:
            return addr
        else:
            return -1
    @value.setter
    def value(self, value: int):
        pass
    def parse_bin(self):
        if isinstance(self._value, int):
            return self._value
        elif isinstance(self._value, str):
            if self.flag_table is not None:
                addr = self.flag_table.get(self._value)
                if addr is not None:
                    return addr
                else:
                    raise ArgOverflowException(f"标记未定义: {self._value}")
            else:
                raise ArgOverflowException(f"无法解析标记引用，没有提供标记表: {self._value}")
        else:
            raise ArgOverflowException(f"无法解析常量值: {self._value}")
    def get_literal(self):
        if self.flag_table is not None and isinstance(self._value, str):
            addr = self.flag_table.get(self._value)
            return f"{self.repr}({addr if addr is not None else '?'})"
        return str(self.value)

class RegArg(Arg):
    name = "寄存器"
    def __init__(self, value: int, repr: str):
        if value < 0 or value > 7:
            raise ArgOverflowException(f"寄存器编号超出范围: {value}")
        super().__init__(value, repr)
    def parse_bin(self):
        return self.value
    def get_literal(self):
        # 从寄存器编号获取寄存器名称
        for reg in RegisterEnum:
            if reg.value == self.value:
                return reg.name
        return f"<Unknown Reg {self.value}>"

ValueArg: TypeAlias = ConstArg | RegArg

class ArgsNotMatchException(Exception):
    pass

def pack_value_arg(arg: Arg) -> int:
    """将ValueArg打包为二进制参数。有效低4位。"""
    if isinstance(arg, ConstArg):
        # 0b0xxx
        return 0b00000000 | (arg.parse_bin() & 0b00000111)
    elif isinstance(arg, RegArg):
        # 0b1xxx
        return 0b00001000 | (arg.parse_bin() & 0b00000111)
    else:
        raise Exception("无法打包未知类型的ValueArg")

class Instruction:
    target_argtypes = [RegArg, ValueArg, ValueArg]
    types_args: list[int | None] = [None, None, None]
    len = 2
    def __init__(self, op: int, args: list[Arg]):
        self.op = op
        self.args = args
    def check_args(self) -> None | str:
        """检查参数是否正确。返回None或str错误信息。"""
        def check_an_args(index: int) -> None | str:
            # 返回None表示通过检查，否则返回错误信息字符串
            # 特例：ValueArg的期望类型字面量是"值"
            arg = self.args[index]
            expected_type = self.target_argtypes[index]
            if not isinstance(arg, expected_type):
                if expected_type is ValueArg:
                    expected = '值(常量或寄存器)'
                else:
                    expected = expected_type.name
                return f"参数{index}类型不匹配，期望{expected}，实际{arg.name}"
            return None
        if len(self.args) != len(self.target_argtypes):
            return f"参数数量不匹配，期望{len(self.target_argtypes)}个，实际{len(self.args)}个"
        for i in range(len(self.target_argtypes)):
            res = check_an_args(i)
            if res is not None:
                return res
            # 对于Const, 根据types_args检查范围
            if isinstance(self.args[i], ConstArg):
                const_max = 7 # 0b111
                arg = self.args[i]
                arg_arg = self.types_args[i]
                if arg_arg is not None:
                    const_max = arg_arg
                if arg.value > const_max:
                    return f"参数{i}常量值超出范围，最大允许{const_max}，实际{arg.value}"
    

    def parse_bin(self) -> bytes:
        """
        :return: 字节码。必须确保之前检查过参数正确性。
        :rtype: btyes
        """
        # 常用：[OpR][VV]
        # 重载以实现不同指令格式的解析
        bin_code = [
            (self.op & 0b11111000) | (self.args[0].parse_bin() & 0b00000111),
            (pack_value_arg(self.args[1]) << 4) | pack_value_arg(self.args[2])
        ]
        return bytes(bin_code)
    
    def get_literal(self) -> str:
        """获取指令的字面量表示，用于信息提示。"""
        arg_literals = [arg.get_literal() for arg in self.args]
        return f"{OpEnum(self.op).name} {' '.join(arg_literals)}"

class Instruction_N(Instruction):
    """无参数指令。PAUSE NOP"""
    target_argtypes = []
    types_args = []
    len = 1
    def __init__(self, op: int, args: list[Arg]):
        super().__init__(op, args)
    def parse_bin(self) -> bytes:
        return bytes([self.op])

class Instruction_R(Instruction):
    """单寄存器指令。INC DEC"""
    target_argtypes = [RegArg]
    types_args = [None]
    len = 1
    def __init__(self, op: int, args: list[Arg]):
        super().__init__(op, args)
    def parse_bin(self) -> bytes:
        bin_code = [
            (self.op & 0b11111000) | (self.args[0].parse_bin() & 0b00000111)
        ]
        return bytes(bin_code)

class Instruction_RV(Instruction):
    """单寄存器，值指令。NOT"""
    target_argtypes = [RegArg, ValueArg]
    types_args = [None, None]
    len = 2
    def __init__(self, op: int, args: list[Arg]):
        super().__init__(op, args)
    def parse_bin(self) -> bytes:
        bin_code = [
            (self.op & 0b11111000) | (self.args[0].parse_bin() & 0b00000111),
            pack_value_arg(self.args[1]) << 4
        ]
        return bytes(bin_code)

class Instruction_VV(Instruction):
    """仅双值指令。CMP"""
    target_argtypes = [ValueArg, ValueArg]
    types_args = [None, None]
    len = 2
    def __init__(self, op: int, args: list[Arg]):
        super().__init__(op, args)
    def parse_bin(self) -> bytes:
        bin_code = [
            self.op,
            (pack_value_arg(self.args[0]) << 4) | pack_value_arg(self.args[1])
        ]
        return bytes(bin_code)

class Instruction_RC8V(Instruction):
    """单寄存器，8位常量，值指令。MOVLZ MOVLN"""
    target_argtypes = [RegArg, ConstArg, ValueArg]
    types_args = [None, 0xFF, None]
    len = 3
    def __init__(self, op: int, args: list[Arg]):
        super().__init__(op, args)
    def parse_bin(self) -> bytes:
        bin_code = [
            (self.op & 0b11111000) | (self.args[0].parse_bin() & 0b00000111),
            self.args[1].parse_bin() & 0xFF,
            pack_value_arg(self.args[2]) << 4
        ]
        return bytes(bin_code)

instructions: dict[str, type[Instruction]] = {
    "PAUSE": Instruction_N,
    "NOP":   Instruction_N,
    "MOVZ":  Instruction,
    "MOVLZ": Instruction_RC8V,
    "MOVN":  Instruction,
    "MOVLN": Instruction_RC8V,
    "ADD":   Instruction,
    "SUB":   Instruction,
    "MUL":   Instruction,
    "DIV":   Instruction,
    "INC":   Instruction_R,
    "DEC":   Instruction_R,
    "CMP":   Instruction_VV,
    "NOT":   Instruction_RV,
    "AND":   Instruction,
    "OR":    Instruction,
    "XOR":   Instruction,
    "SHL":   Instruction,
    "SHR":   Instruction,
}

class Flag:
    def __init__(self, name: str):
        self.name = name

# 变量名匹配：仅包含大小写字母、数字、下划线
rematch_varname = re.compile(r"^[A-Za-z0-9_]*$")
# 更严格的变量名匹配：首字符只能是字母或下划线
rematch_varname_strict = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# 可能无效的变量名匹配：只包含数字
rematch_varname_invalid = re.compile(r"^\d+$")

def parse_number(s: str) -> Optional[int]:
    """尝试将字符串解析为数字。
    支持的写法：
    - 十进制整数: 123, 456d
    - 十六进制整数: 0x1A3F, 3Ah
    - 八进制整数： 0o173, 173o
    - 二进制整数： 0b101101, 101101b
    若解析失败，返回None。
    """
    s = s.strip().upper()
    try:
        if s.endswith('D'):
            return int(s[:-1], 10)
        elif s.endswith('H'):
            return int(s[:-1], 16)
        elif s.endswith('O'):
            return int(s[:-1], 8)
        elif s.endswith('B'):
            return int(s[:-1], 2)
        elif s.startswith('0X'):
            return int(s, 16)
        elif s.startswith('0O'):
            return int(s, 8)
        elif s.startswith('0B'):
            return int(s, 2)
        else:
            return int(s, 10)
    except ValueError:
        return None

def print_error(line_number: int, message: str, line: str, title: str = "错误"):
    """打印编译错误信息。"""
    print(f"""\
{title}: {message}
    {line_number} | {line}
""")
    
ParseInstruction_BaseType: TypeAlias = Instruction | Flag | str | None
class ParseInstructionResult:
    base: ParseInstruction_BaseType = None
    warn: Optional[str] = None

def parse_instruction(line: str, flag_table: dict[str, int]) -> ParseInstructionResult:
    """匹配指令。Flag表示匹配到flag。若匹配不成功，返回str错误信息。None表示空行。"""
    line = line.strip()
    ret = ParseInstructionResult()
    if line == "":
        return ret
    # 检查是否是flag
    if line.endswith(":"):
        var = line[:-1].strip()
        # 检查是否符合变量名规范
        if rematch_varname.match(var) is None:
            ret.base = f"无效的flag '{var}'"
            return ret
        ret.base = Flag(var)
        # 检查是否无效的变量名
        if rematch_varname_invalid.match(var) is not None:
            ret.warn = f"该flag只包含数字，我确信它不会在代码中被解析"
        # 检查是否符合更严格的变量名规范
        elif rematch_varname_strict.match(var) is None:
            ret.warn = f"该flag不符合更严格的变量名规范"
        return ret

    # 将逗号替换为空格
    line = line.replace(",", " ")
    # 按空格分割字符串
    ops = line.split()
    # 指令名
    op = ops[0].upper()
    ins = instructions.get(op)
    if ins is None:
        ret.base =  f"未知的指令：{op}"
        return ret
    args: list[Arg] = []
    for arg_str in ops[1:]:
        arg_str_upper = arg_str.upper()
        # 若匹配到寄存器
        if arg_str_upper in RegisterEnum.__members__:
            reg_value = RegisterEnum[arg_str_upper].value
            args.append(RegArg(reg_value, arg_str_upper))
        # 若is_number返回数，则认为是常量
        else:
            num_value = parse_number(arg_str)
            if num_value is not None:
                args.append(ConstArg(num_value, arg_str))
            else:
                # 认为是flag引用
                args.append(ConstArg(arg_str, arg_str, flag_table=flag_table))
    instruction_instance = ins(OpEnum[op].value, args)
    ret.base = instruction_instance
    return ret

BinCodeType: TypeAlias = list[tuple[bytes, str]]

def compile(args: argparse.Namespace, code_raw: str) -> tuple[BinCodeType, bool]:
    """
    :param code: 汇编代码
    :type code: str
    :return: 字节码, 是否有错误
    :rtype: tuple[bytearray, bool]
    """
    cur_addr = 0
    line_instructions: list[tuple[int, Instruction]] = []
    flag_table: dict[str, int] = {}
    code = remove_comments_preserve_lines(code_raw) # 移除注释但保留行号信息
    code_raw_lines = code_raw.splitlines()
    # 初步解析，生成指令
    # print(code)
    has_error = False
    for line_number, line in enumerate(code.splitlines(), start=1):
        #  line = line.strip()
        res_objectd = parse_instruction(line, flag_table)
        res = res_objectd.base
        # 输出warn
        if res_objectd.warn is not None and not args.no_warn:
            print_error(line_number, res_objectd.warn, code_raw_lines[line_number - 1], title="警告")
        if res is None:
            continue
        elif isinstance(res, str):
            print_error(line_number, res, line)
            has_error = True
            continue
        elif isinstance(res, Flag):
            flag_name = res.name
            if flag_name in flag_table:
                # print(f"第 {line_number} 行编译错误: 重复的标记 '{flag_name}'")
                print_error(line_number, f"重复的标记 '{flag_name}'", code_raw_lines[line_number - 1])
                has_error = True
            else:
                # print(f"定义标记 '{flag_name}' 地址 {cur_addr}")

                flag_table[flag_name] = cur_addr
            continue
        # 检查参数
        check_result = res.check_args()
        if check_result is not None:
            # print(f"第 {line_number} 行编译错误: {check_result}")
            print_error(line_number, check_result, code_raw_lines[line_number - 1])
            has_error = True
            continue
        # 增加指令长度
        cur_addr += res.len
        # 添加指令
        line_instructions.append((line_number, res))
    # 生成字节码
    bin_code = []
    for line_number, instruction in line_instructions:
        # 检查
        check_result = instruction.check_args()
        if check_result is not None:
            # print(f"第 {line_number} 行编译错误: {check_result}")
            print_error(line_number, check_result, code_raw_lines[line_number - 1])
            has_error = True
            continue
        try:
            bin_inst = instruction.parse_bin()
            bin_code.append((bin_inst, instruction.get_literal()))
        except Exception as e:
            # print(f"第 {line_number} 行编译错误: {str(e)}")
            print_error(line_number, str(e), code_raw_lines[line_number - 1])
            has_error = True
    
    return bin_code, has_error

def out_bin(bytecode: BinCodeType) -> str:
    string = f"""\
 Addr       Byte             ASM
-----------------------------------------
"""
    addr = 0
    # 遍历列表
    for bin_inst, asm in bytecode:
        # 遍历字节
        for i, byte in enumerate(bin_inst):
            string += f"{addr:>4} | "
            byte_bin = ' '.join(f"{byte:08b}") + ' '
            string += byte_bin + '|'
            if i == 0:
                string += f" {asm}"
            addr += 1
            string += '\n'
    return string

def pack_bin(bytecode: BinCodeType) -> bytearray:
    """打包成buytearray"""
    return bytearray(b''.join([inst for inst, _ in bytecode]))

def main():
    parser = argparse.ArgumentParser(description="DZC-8M Instruction ASM Compiler")
    parser.add_argument("file", help="输入的汇编代码文件")
    parser.add_argument("-o", "--output", help="将字节码输出到文件。不指定则不输出到文件")
    parser.add_argument("-nob", "--no-output_binary", action="store_true", help="不输出二进制字节码")
    parser.add_argument("--no-warn", action="store_true", help="不显示警告")
    parser.add_argument("--version", action="version", version=f"Eggy Assembler Compiler\n{__version__}\nfor DZC-8M Plus Instruction Set")
    args = parser.parse_args()
    # 读取文件内容
    with open(args.file, "r", encoding="utf-8") as f:
        code = f.read()
    # 编译
    bytecode, has_error = compile(args, code)
    if has_error:
        print("编译失败，存在错误。")
        return 1
    # 输出字节码
    if not args.no_output_binary:
        print(out_bin(bytecode))
    # 如果指定了输出文件，则写入文件
    if args.output:
        with open(args.output, "wb") as f:
            f.write(pack_bin(bytecode))
        print(f"二进制字节码已输出到 {args.output}")
    return 0

if __name__ == "__main__":
    sys.exit(main())