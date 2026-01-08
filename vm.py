import sys, os
import argparse

PC = 0
AF = 1
SP = 2
GIO = 3
R0 = 4
R1 = 5
R2 = 6
R3 = 7

class Ctx_t:
    Registers: list[int] = [
         0x00,  # PC
         0x00,  # AF
         0x00,  # SP
         0x00,  # GIO
         0x00,  # R0
         0x00,  # R1
         0x00,  # R2
         0x00,  # R3
    ]
        
    Program: bytes = b'\x00' * 0xFF
    Program_max_addr: int = 0x0 # 超出max_addr识别为overflow

    Pause_signal: bool = False # 暂停信号。和DZC-8M的暂停信号一致。需自行复位。

class InstructionRunner:
    def __init__(self, ctx: Ctx_t):
        self.ctx = ctx
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
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        targetValue = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        Condition = self.__value_get_value(program_d1 & 0b00001111)

        if not Condition:
            self.ctx.Registers[outReg] = targetValue

        return 2
    def __run_movn(self):
        # MOVN:[00110R][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)
        
        outReg = program_d0 & 0b00000111
        targetValue = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        Condition = self.__value_get_value(program_d1 & 0b00001111)

        if Condition:
            self.ctx.Registers[outReg] = targetValue

        return 2
    def __run_movlz(self):
        # MOVLZ:00101R][C(8)][Vxxxx]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 3)
        program_d1 = self.get_program_from_addr(pc - 2)
        program_d2 = self.get_program_from_addr(pc - 1)
        

        outReg = program_d0 & 0b00000111
        targetValue = program_d1
        Condition = self.__value_get_value((program_d2 & 0b11110000) >> 4)

        if not Condition:
            self.ctx.Registers[outReg] = targetValue

        return 3
    def __run_movln(self):
        # MOVLN:00111R][C(8)][Vxxxx]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 3)
        program_d1 = self.get_program_from_addr(pc - 2)
        program_d2 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        targetValue = program_d1
        Condition = self.__value_get_value((program_d2 & 0b11110000) >> 4)

        if Condition:
            self.ctx.Registers[outReg] = targetValue

        return 3
    def __run_add(self):
        # ADD: [0100xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        out = arg1 + arg2
        out = self.__af_set((arg1, arg2, out), False)
        self.ctx.Registers[outReg] = out
        return 2
    def __run_sub(self):
        # SUB: [0101xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        out = arg1 - arg2
        out = self.__af_set((arg1, arg2, out), True)
        self.ctx.Registers[outReg] = out
        return 2
    def __run_addc(self):
        # ADDC:[0110xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

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
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

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
        program_d0 = self.get_program_from_addr(self.ctx.Registers[PC] - 1)

        outReg = program_d0 & 0b00000111
        out = self.ctx.Registers[outReg] + 1
        out = self.__af_set((self.ctx.Registers[outReg], 1, out), False)
        self.ctx.Registers[outReg] = out
        return 1
    def __run_dec(self):
        # DEC: [10001R]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[PC] - 1)

        outReg = program_d0 & 0b00000111
        out = self.ctx.Registers[outReg] - 1
        out = self.__af_set((self.ctx.Registers[outReg], 1, out), True)
        self.ctx.Registers[outReg] = out
        return 1
    def __run_cmp(self):
        # CMP: [1001x-][VV]
        # program_d0 = self.get_program_from_addr(self.ctx.Registers[PC] - 2)
        program_d1 = self.get_program_from_addr(self.ctx.Registers[PC] - 1)

        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.__af_set((arg1, arg2, arg1 - arg2), True)
        return 2

    def __run_not(self):
        # NOT: [1010xR][Vxxxx]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)

        self.ctx.Registers[outReg] = ~arg1 & 0xFF
        return 2
    def __run_and(self):
        # AND: [1011xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 & arg2
        return 2
    def __run_or(self):
        # OR:  [1100xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 | arg2
        return 2
    def __run_xor(self):
        # XOR: [1101xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 ^ arg2
        return 2
    def __run_shl(self):
        # SHL: [1110xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = (arg1 << arg2) & 0xFF
        return 2
    def __run_shr(self):
        # SHR: [1111xR][VV]
        pc = self.ctx.Registers[PC]
        program_d0 = self.get_program_from_addr(pc - 2)
        program_d1 = self.get_program_from_addr(pc - 1)
        
        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = (arg1 >> arg2)
        return 2
    
    command_table = {
        0b00000: (__run_pause, 1),
        0b00001: (__run_pause, 1),
        0b00010: (__run_nop, 1),
        0b00011: (__run_nop, 1),
        0b00100: (__run_movz, 2),
        0b00101: (__run_movlz, 3),
        0b00110: (__run_movn, 2),
        0b00111: (__run_movln, 3),
        0b01000: (__run_add, 2),
        0b01001: (__run_add, 2),
        0b01010: (__run_sub, 2),
        0b01011: (__run_sub, 2),
        0b01100: (__run_addc, 2),
        0b01101: (__run_addc, 2),
        0b01110: (__run_subb, 2),
        0b01111: (__run_subb, 2),
        0b10000: (__run_inc, 1),
        0b10001: (__run_dec, 1),
        0b10010: (__run_cmp, 2),
        0b10011: (__run_cmp, 2),
        0b10100: (__run_not, 2),
        0b10101: (__run_not, 2),
        0b10110: (__run_and, 2),
        0b10111: (__run_and, 2),
        0b11000: (__run_or, 2),
        0b11001: (__run_or, 2),
        0b11010: (__run_xor, 2),
        0b11011: (__run_xor, 2),
        0b11100: (__run_shl, 2),
        0b11101: (__run_shl, 2),
        0b11110: (__run_shr, 2),
        0b11111: (__run_shr, 2),
    }

    def run_step(self):
        # 获取指令头
        op = self.ctx.Program[self.ctx.Registers[PC]]
        head = op >> 3

        func, size = self.command_table[head]
        # dbg: 输出pc以及add之后的所有指令
        _start = self.ctx.Registers[PC]
      # for i in range(_start, _start + size):
      #     print(f"{i:02X}: {self.ctx.Program[i]:08b}")
        # 更新PC
        self.ctx.Registers[PC] = (self.ctx.Registers[PC] + size) & 0xFF
        # 执行指令
        func(self)

# Test
if __name__ == '__main__':
    # 解析参数：file
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='file binary to run')
    args = parser.parse_args()
    # 初始化虚拟机
    ctx = Ctx_t()
    vm = InstructionRunner(ctx)
    # 读取文件，写入到内存
    with open(args.file, 'rb') as f:
        ctx.Program = f.read()
        #填充到256字节
        ctx.Program += b'\x00' * (0xFF - len(ctx.Program))
    while True:
        vm.run_step()
        if ctx.Pause_signal:
            print(f"""
            PC: {vm.ctx.Registers[PC]}
            AF: {vm.ctx.Registers[AF]}
            SP: {vm.ctx.Registers[SP]}
            GIO: {vm.ctx.Registers[GIO]}
            R0: {vm.ctx.Registers[R0]}
            R1: {vm.ctx.Registers[R1]}
            R2: {vm.ctx.Registers[R2]}
            R3: {vm.ctx.Registers[R3]}
            """)
            input("Pausing, press enter to continue...")
            ctx.Pause_signal = False
            print("Continue")
