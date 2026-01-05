import sys, os
import argparse

from typing import Callable

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

class InstructionRunner:
    def __init__(self, ctx: Ctx_t):
        self.ctx = ctx
    def get_program_from_addr(self, addr: int) -> int:
        return self.ctx.Program[addr % 0xFF]
    def __value_get_value(self, val: int) -> int:
        if val & 0b1000: #R
            return self.ctx.Registers[val & 0b0111]
        else: # C
            return val
    def __af_set(self, ops: tuple[int, int, int], is_sub: bool) -> int:
        # 设置AF符号位。注意out是a和b直接计算没有取模得到的。返回out对0xFF取模后的值
        a = ops[0]
        b = ops[1]
        out = ops[2]

        sign_a = a & 0b10000000
        sign_b = b & 0b10000000
        sign_out = out & 0b10000000
        
        AF = self.ctx.Registers[1]
        # XXXXXOCZ
        AF = AF & 0b11111000
        AF |= out == 0x00 # ZF
        AF |= (out < 0 or out > 0xFF) << 1 # CF
        AF |= (
            1
            if ((sign_a == sign_b) ^ is_sub) and (sign_out != sign_a)
            else 0
        ) << 2 # OF
        return out & 0xFF
    def __run_movz(self):
        # MOVZ:  [00100R][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        targetValue = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        Condition = self.__value_get_value(program_d1 & 0b00001111)

        if not Condition:
            self.ctx.Registers[outReg] = targetValue

        return 2

    def __run_movn(self):
        # MOVN:  [00110R][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        targetValue = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        Condition = self.__value_get_value(program_d1 & 0b00001111)

        if Condition:
            self.ctx.Registers[outReg] = targetValue

        return 2

    def __run_movlz(self):
        # MOVLZ: [00101R][C(8)][Vxxxx]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)
        program_d2 = self.get_program_from_addr(self.ctx.Registers[0] + 2)

        outReg = program_d0 & 0b00000111
        targetValue = program_d1
        Condition = self.__value_get_value((program_d2 & 0b11110000) >> 4)

        if not Condition:
            self.ctx.Registers[outReg] = targetValue

        return 3

    def __run_movln(self):
        # MOVLN: [00111R][C(8)][Vxxxx]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)
        program_d2 = self.get_program_from_addr(self.ctx.Registers[0] + 2)

        outReg = program_d0 & 0b00000111
        targetValue = program_d1
        Condition = self.__value_get_value((program_d2 & 0b11110000) >> 4)

        if Condition:
            self.ctx.Registers[outReg] = targetValue

        return 3

    def __run_add(self):
        # ADD:   [0100xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        out = arg1 + arg2
        out = self.__af_set((arg1, arg2, out), False)
        self.ctx.Registers[outReg] = out
        return 2

    def __run_sub(self):
        # SUB:   [0101xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        out = arg1 - arg2
        out = self.__af_set((arg1, arg2, out), True)
        self.ctx.Registers[outReg] = out
        return 2
    
    def __run_addc(self):
        # ADDC:  [0110xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)
        CF = self.ctx.Registers[1] & 0b00000010

        out = arg1 + arg2 + CF
        out = self.__af_set((arg1, arg2, out), False)
        self.ctx.Registers[outReg] = out
        return 2

    def __run_subb(self):
        # SUBC:  [0111xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)
        CF = self.ctx.Registers[1] & 0b00000010

        out = arg1 - arg2 - CF
        out = self.__af_set((arg1, arg2, out), True)
        self.ctx.Registers[outReg] = out
        return 2

    def __run_inc(self):
        # INC:   [10000R]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])

        outReg = program_d0 & 0b00000111
        out = self.ctx.Registers[outReg] + 1
        out = self.__af_set((self.ctx.Registers[outReg], 1, out), False)
        self.ctx.Registers[outReg] = out
        return 1
    def __run_dec(self):
        # DEC:   [10001R]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])

        outReg = program_d0 & 0b00000111
        out = self.ctx.Registers[outReg] - 1
        out = self.__af_set((self.ctx.Registers[outReg], 1, out), True)
        self.ctx.Registers[outReg] = out
        return 1

    def __run_cmp(self):
        # CMP:   [1001x-][VV]
        # program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.__af_set((arg1, arg2, arg1 - arg2), True)
        return 2

    def __run_not(self):
        # NOT:   [1010xR][Vxxxx]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)

        self.ctx.Registers[outReg] = ~arg1 & 0xFF
        return 2

    def __run_and(self):
        # AND:   [1011xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 & arg2
        return 2

    def __run_or(self):
        # OR:    [1100xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 | arg2
        return 2

    def __run_xor(self):
        # XOR:   [1101xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = arg1 ^ arg2
        return 2

    def __run_shl(self):
        # SHL:   [1110xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)

        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = (arg1 << arg2) & 0xFF
        return 2

    def __run_shr(self):
        # SHR:   [1111xR][VV]
        program_d0 = self.get_program_from_addr(self.ctx.Registers[0])
        program_d1 = self.get_program_from_addr(self.ctx.Registers[0] + 1)
        outReg = program_d0 & 0b00000111
        arg1 = self.__value_get_value((program_d1 & 0b11110000) >> 4)
        arg2 = self.__value_get_value(program_d1 & 0b00001111)

        self.ctx.Registers[outReg] = (arg1 >> arg2) & 0xFF
        return 2
    
    command_table = {
        0b00000: None, # PAUSE
        0b00001: None, # PAUSE
        0b00010: None, # NOP
        0b00011: None, # NOP
        0b00100: __run_movz,
        0b00101: __run_movlz,
        0b00110: __run_movn,
        0b00111: __run_movln,
        0b01000: __run_add,
        0b01001: __run_add,
        0b01010: __run_sub,
        0b01011: __run_sub,
        0b01100: __run_addc,
        0b01101: __run_addc,
        0b01110: __run_subb,
        0b01111: __run_subb,
        0b10000: __run_inc,
        0b10001: __run_dec,
        0b10010: __run_cmp,
        0b10011: __run_cmp,
        0b10100: __run_not,
        0b10101: __run_not,
        0b10110: __run_and,
        0b10111: __run_and,
        0b11000: __run_or,
        0b11001: __run_or,
        0b11010: __run_xor,
        0b11011: __run_xor,
        0b11100: __run_shl,
        0b11101: __run_shl,
        0b11110: __run_shr,
        0b11111: __run_shr
    }