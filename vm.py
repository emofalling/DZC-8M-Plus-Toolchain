from typing import Callable

PC = 0
AF = 1
SP = 2
IO = 3
R0 = 4
R1 = 5
R2 = 6
R3 = 7

reg_name_map = {
    0: 'PC',
    1: 'AF',
    2: 'SP',
    3: 'IO',
    4: 'R0',
    5: 'R1',
    6: 'R2',
    7: 'R3',
}

class Ctx_t:
    Registers: list[int] = [
         0x00,  # PC
         0x00,  # AF
         0x00,  # SP
         0x00,  # IO
         0x00,  # R0
         0x00,  # R1
         0x00,  # R2
         0x00,  # R3
    ]
        
    Program: bytearray = bytearray(0xFF) # 程序存储区
    Program_max_addr: int = 0x0 # 超出max_addr识别为overflow

    Pause_signal: bool = False # 暂停信号。和DZC-8M的暂停信号一致。需自行复位。

class InstructionRunner:
    def __init__(self, ctx: Ctx_t):
        self.ctx = ctx
        self.cur_addr = 0 # 当前指令地址
        self.program_d0 = 0 # 当前addr + 0的程序字节
        self.program_d1 = 0 # 当前addr + 1的程序字节
        self.program_d2 = 0 # 当前addr + 2的程序字节
        self.command_table: dict[int, tuple[Callable, int]] = {
            0b00000: (self.__run_pause, 1),
            0b00001: (self.__run_pause, 1),
            0b00010: (self.__run_nop, 1),
            0b00011: (self.__run_nop, 1),
            0b00100: (self.__run_movz, 2),
            0b00101: (self.__run_movlz, 3),
            0b00110: (self.__run_movn, 2),
            0b00111: (self.__run_movln, 3),
            0b01000: (self.__run_add, 2),
            0b01001: (self.__run_add, 2),
            0b01010: (self.__run_sub, 2),
            0b01011: (self.__run_sub, 2),
            0b01100: (self.__run_addc, 2),
            0b01101: (self.__run_addc, 2),
            0b01110: (self.__run_subb, 2),
            0b01111: (self.__run_subb, 2),
            0b10000: (self.__run_inc, 1),
            0b10001: (self.__run_dec, 1),
            0b10010: (self.__run_cmp, 2),
            0b10011: (self.__run_cmp, 2),
            0b10100: (self.__run_not, 2),
            0b10101: (self.__run_not, 2),
            0b10110: (self.__run_and, 2),
            0b10111: (self.__run_and, 2),
            0b11000: (self.__run_or, 2),
            0b11001: (self.__run_or, 2),
            0b11010: (self.__run_xor, 2),
            0b11011: (self.__run_xor, 2),
            0b11100: (self.__run_shl, 2),
            0b11101: (self.__run_shl, 2),
            0b11110: (self.__run_shr, 2),
            0b11111: (self.__run_shr, 2),
        }
    def get_program_from_addr(self, addr: int) -> int:
        return self.ctx.Program[addr % 0xFF]
    def __value_get_value(self, val: int) -> int:
        if val & 0b1000: #R
            return self.ctx.Registers[val & 0b0111]
        else: #C
            return val
    def __af_set(self, ops: tuple[int, int, int], is_sub: bool) -> int:
        # 设置AF符号位。注意out是a和b直接计算没有取模得到的。返回out对0xFF取模后的值
        a = ops[0]
        b = ops[1]
        out = ops[2]

        sign_a = a & 0b10000000
        sign_b = b & 0b10000000
        sign_out = out & 0b10000000
        
        af = self.ctx.Registers[AF]
        # XXXXXOCZ
        af = af & 0b11111000
        af |= out == 0x00 # ZF
        af |= (out < 0 or out > 0xFF) << 1 # CF
        af |= (
            1
            if ((sign_a == sign_b) ^ is_sub) and (sign_out != sign_a)
            else 0
        ) << 2 # OF
        self.ctx.Registers[AF] = af
        return out & 0xFF
    
    def __run_nop(self):
        # NOP:[0001x-]
        return 1
    def __run_pause(self):
        # PAUSE:[0000x-]
        self.ctx.Pause_signal = True
        return 1
    
    def __run_movz(self):
        # MOVZ:[00100R][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        targetValue = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        Condition = self.__value_get_value(program_d1 & 0b00001111)

        if not Condition:
            self.ctx.Registers[outReg] = targetValue

        return 2
    def __run_movn(self):
        # MOVN:[00110R][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1
        
        outReg = program_d0 & 0b00000111
        targetValue = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        Condition = self.__value_get_value(program_d1 & 0b00001111)

        if Condition:
            self.ctx.Registers[outReg] = targetValue

        return 2
    def __run_movlz(self):
        # MOVLZ:00101R][C(8)][Vxxxx]
        program_d0 = self.program_d0
        program_d1 = self.program_d1
        program_d2 = self.program_d2
        

        outReg = program_d0 & 0b00000111
        targetValue = program_d1
        Condition = self.__value_get_value((program_d2 & 0b11110000) >> 4)

        if not Condition:
            self.ctx.Registers[outReg] = targetValue

        return 3
    def __run_movln(self):
        # MOVLN:00111R][C(8)][Vxxxx]
        program_d0 = self.program_d0
        program_d1 = self.program_d1
        program_d2 = self.program_d2

        outReg = program_d0 & 0b00000111
        targetValue = program_d1
        Condition = self.__value_get_value((program_d2 & 0b11110000) >> 4)

        if Condition:
            self.ctx.Registers[outReg] = targetValue

        return 3
    def __run_add(self):
        # ADD: [0100xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        out = arg1 + arg2
        out = self.__af_set((arg1, arg2, out), False)
        self.ctx.Registers[outReg] = out
        return 2
    def __run_sub(self):
        # SUB: [0101xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        out = arg1 - arg2
        out = self.__af_set((arg1, arg2, out), True)
        self.ctx.Registers[outReg] = out
        return 2
    def __run_addc(self):
        # ADDC:[0110xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)
        CF = self.ctx.Registers[1] & 0b00000010

        out = arg1 + arg2 + CF
        out = self.__af_set((arg1, arg2, out), False)
        self.ctx.Registers[outReg] = out
        return 2
    def __run_subb(self):
        # SUBC:[0111xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)
        CF = self.ctx.Registers[1] & 0b00000010

        out = arg1 - arg2 - CF
        out = self.__af_set((arg1, arg2, out), True)
        self.ctx.Registers[outReg] = out
        return 2
    def __run_inc(self):
        # INC: [10000R]
        program_d0 = self.program_d0

        outReg = program_d0 & 0b00000111
        out = self.ctx.Registers[outReg] + 1
        out = self.__af_set((self.ctx.Registers[outReg], 1, out), False)
        self.ctx.Registers[outReg] = out
        return 1
    def __run_dec(self):
        # DEC: [10001R]
        program_d0 = self.program_d0

        outReg = program_d0 & 0b00000111
        out = self.ctx.Registers[outReg] - 1
        out = self.__af_set((self.ctx.Registers[outReg], 1, out), True)
        self.ctx.Registers[outReg] = out
        return 1
    def __run_cmp(self):
        # CMP: [1001x-][VV]
        # program_d0 = self.get_program_from_addr(self.ctx.Registers[PC] - 2)
        program_d1 = self.program_d1

        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.__af_set((arg1, arg2, arg1 - arg2), True)
        return 2

    def __run_not(self):
        # NOT: [1010xR][Vxxxx]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)

        self.ctx.Registers[outReg] = ~arg1 & 0xFF
        return 2
    def __run_and(self):
        # AND: [1011xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 & arg2
        return 2
    def __run_or(self):
        # OR:  [1100xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 | arg2
        return 2
    def __run_xor(self):
        # XOR: [1101xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 ^ arg2
        return 2
    def __run_shl(self):
        # SHL: [1110xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = (arg1 << arg2) & 0xFF
        return 2
    def __run_shr(self):
        # SHR: [1111xR][VV]
        program_d0 = self.program_d0
        program_d1 = self.program_d1
        
        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = (arg1 >> arg2)
        return 2
    
    def run_step(self):
        # 获取前3位指令
        pc = self.ctx.Registers[PC]
        self.cur_addr = pc
        self.program_d0 = self.get_program_from_addr(pc)
        self.program_d1 = self.get_program_from_addr(pc + 1)
        self.program_d2 = self.get_program_from_addr(pc + 2)
        # 取头
        head = self.program_d0 >> 3
        # 获取函数
        func, size = self.command_table[head]
        # PC增偏移量
        self.ctx.Registers[PC] = (pc + size) & 0xFF
        # 执行函数
        func()

ANSI_CURSOR_UP = '\x1b[1A'
ANSI_CURSOR_UPS = lambda lines: f'\x1b[{lines}A'
ANSI_CURSOR_DOWN = '\x1b[1B'
ANSI_CURSOR_DOWNS = lambda lines: f'\x1b[{lines}B'
ANSI_CURSOR_MOVE_UD = lambda lines: ANSI_CURSOR_DOWNS(lines) if lines > 0 else (ANSI_CURSOR_UPS(-lines) if lines < 0 else '')
ANSI_CURSOR_LEFT = '\r'
ANSI_CLEAR_LINE = '\x1b[2K'

FILL_TRIANGLE = "\u25BA"
CIRCLE = "\u25CB"

        
if __name__ == '__main__':
    import time
    import sys
    import argparse
    import signal

    stdin = sys.stdin
    stdout = sys.stdout
    # 解析参数：file
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='file binary or json to run')
    parser.add_argument('-D', '--debug', help='若启用此项，file必须为json文件。不启用此项时，file必须为二进制文件', action='store_true')
    parser.add_argument('-d', '--delay', type=float, help='每步执行延迟，单位为秒。默认不执行。负值表示单步调试', default=0.0)
    parser.add_argument('-F', '--full-src', help='若启用此项，则显示所有源代码行，提供更清晰的代码提示。否则，只显示当前行，以便快速定位', action='store_true')
    parser.add_argument('--ignore-pause', help='若启用此项，则忽略PAUSE信号。否则，当PAUSE信号被触发时，程序仍继续执行', action='store_true')
    args = parser.parse_args()

    # 初始化虚拟机
    ctx = Ctx_t()
    vm = InstructionRunner(ctx)

    debug: bool = args.debug
    delay: float = args.delay
    single_step = delay < 0.0
    full_src = args.full_src
    ignore_pause = args.ignore_pause

    program: bytes
    src: str | None
    lines: list[int]
    src_lines: list[str] = []

    last_curaddr = 2**32 - 1 # 上一次的地址。仅在debug -F模式下使用。

    # 读取文件
    if debug: # JSON debug
        import json, base64
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        program = base64.b64decode(data["bin"])
        src = data["src"]
        lines = data["lines"]
        src_lines = src.splitlines() # type: ignore
    else: # 二进制
        with open(args.file, 'rb') as f:
            program = f.read()
            src = None
            lines = []
    
    # 如果program大于0xFF，则发送信息截断
    if len(program) > 0xFF:
        print("输入的程序大于256字节。将从0x00开始截断到0xFF。")
        ctx.Program[:] = program[:0xFF]
    else: #等于或小于256字节。补零。
        ctx.Program[:len(program)] = program
    is_exit = False
    
    def signal_handler(signum, frame):
        global is_exit
        is_exit = True
    signal.signal(signal.SIGINT, signal_handler)

    def clearlines(lines: int):
        stdout.write(ANSI_CURSOR_LEFT + (ANSI_CURSOR_UP + ANSI_CLEAR_LINE) * 2)

    def line_format(line: int) -> str:
        return f"{line+1:>4}| {src_lines[line]}\n"

    def get_line_str(addr: int) -> str:
        try:
            line = lines[addr]
            return line_format(line)
        except IndexError:
            return f"{f'0x{addr:X}':>6}: 0x{ctx.Program[addr]:02X}\n"

    if full_src:
        # 输出所有行
        for i in range(len(src_lines)):
            stdout.write(line_format(i))
        # 移到行首
        stdout.write(ANSI_CURSOR_LEFT + ANSI_CURSOR_UPS(len(src_lines)))

    while True:
        vm.run_step()
        main = ""
        pause_info = []

        if debug: 
            if full_src:
                # 将上一个cur_addr的行开头改为空格
                try:
                    last_line = lines[last_curaddr]
                    stdout.write(ANSI_CURSOR_DOWNS(last_line) + ' ' + ANSI_CURSOR_LEFT)
                except IndexError: last_line = -1
                try:
                    cur_line = lines[vm.cur_addr]
                    # 计算差值
                    if last_line == -1: diff = cur_line
                    else: diff = cur_line - last_line
                    # 三角形
                    stdout.write(ANSI_CURSOR_MOVE_UD(diff) + FILL_TRIANGLE + ANSI_CURSOR_LEFT)
                except IndexError: cur_line = -1
                last_curaddr = vm.cur_addr
                try:
                    next_line = lines[vm.ctx.Registers[PC]]
                    # 计算差值
                    if cur_line == -1: diff = next_line
                    else: diff = next_line - cur_line
                    # 圆形
                    stdout.write(ANSI_CURSOR_MOVE_UD(diff) + CIRCLE + ANSI_CURSOR_LEFT)
                except IndexError: next_line = 0
                # 移到行尾
                stdout.write(ANSI_CURSOR_MOVE_UD(len(src_lines) - next_line))

            else:
                main += FILL_TRIANGLE + get_line_str(vm.cur_addr)
                main += CIRCLE + get_line_str(ctx.Registers[PC])
        for i in range(8):
            n = ctx.Registers[i]
            s08b = f"{n:08b}"
            sn = f"{' '.join([*s08b])} = {n}"
            sn_main = f"{reg_name_map[i]} = {sn}"
            # PC = 1 1 1 1 1 1 1 1 = 255, 最大长度26
            # 添加适量的空格
            main += sn_main + ' ' * (26 - len(sn_main)) + '\n'

        if ctx.Pause_signal:
            pause_info.append("PAUSE")
            ctx.Pause_signal = False
        
        if single_step:
            pause_info.append("SINGLE_STEP")
        
        if pause_info:
            main += f"Pause by {','.join(pause_info)}. Press Enter to continue, or input command.\n"
        
        stdout.write(main)
        
        if pause_info and not ignore_pause:
            command = stdin.readline()
        else: #延迟
            if delay > 0.0: time.sleep(delay)
        
        if is_exit:
            if pause_info:
                # 向上移动并清行
                clearlines(1)
            stdout.write("Exit.\n")
            exit(0)
        
        if pause_info:
            # 对于未忽略的pause, 向上移动并清行，两次; 否则1次
            clearlines(1 if ignore_pause else 2)
        
        
        # 发送8个移行指令，清寄存器表
        stdout.write(ANSI_CURSOR_LEFT + ANSI_CURSOR_UPS(8))

        if debug:
            if full_src:
                # 移动到行首
                stdout.write(ANSI_CURSOR_UPS(len(src_lines)))
                # stdout.write(f"u{len(src_lines)}." + ANSI_CURSOR_LEFT)
            else: # 非full时清行
                clearlines(2)