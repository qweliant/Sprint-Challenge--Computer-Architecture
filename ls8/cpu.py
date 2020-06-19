"""CPU functionality."""
import re
import sys
import tty
import termios
from datetime import datetime

# ALU INSTRUCTIONS
MUL = 0b10100010
ADD = 0b10100000
SUB = 0b10100001
DIV = 0b10100011
MOD = 0b10100100
INC = 0b01100101
DEC = 0b01100110
CMP = 0b10100111
AND = 0b10101000
NOT = 0b01101001
OR = 0b10101010
XOR = 0b10101011
SHL = 0b10101100
SHR = 0b10101101

# PC MUTATORS
CALL = 0b01010000
RET = 0b00010001
INT = 0b01010010
IRET = 0b00010011
JMP = 0b01010100
JEQ = 0b01010101
JNE = 0b01010110
JGT = 0b01010111
JLT = 0b01011000
JLE = 0b01011001
JGE = 0b01011010

# OTHER
NOP = 0b00000000
HLT = 0b00000001
LDI = 0b10000010
LD = 0b10000011
ST = 0b10000100
PUSH = 0b01000101
POP = 0b01000110
PRN = 0b01000111
PRA = 0b01001000


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        # program counter
        self.pc = 0  # program counter
        # 8 new reg
        self.reg = [0] * 8  # register
        # memory storage for ram
        self.ram = [0] * 256
        self.sp = 0xF3  # stack pointer - points at the value at the top of the stack
        self.fl = 0b11000000  # Flags Register

        self.branchtable = {
            MUL : self.handle_mul,
            ADD : self.handle_add,
            LDI : self.handle_ldi,
            HLT : self.handle_hlt,
            PRN : self.handle_prn,
            POP : self.handle_pop,
            PUSH : self.handle_push,
            RET : self.handle_ret,
            CALL : self.handle_call,
            JMP : self.handle_jmp,
            ST : self.handle_st,
            IRET : self.handle_iret,
            JEQ  : self.handle_jeq,
            JNE : self.handle_jne,
            CMP : self.handle_cmp

        }
        

    # Interrupt Mask is R5
    @property
    def IM(self):
        return self.reg[5]

    @IM.setter
    def IM(self, value):
        self.reg[5] = value

    # Interrupt Status is R6
    @property
    def IS(self):
        return self.reg[6]

    @IS.setter
    def IS(self, value):
        self.reg[6] = value

    def load(self):
        """Load a program into memory."""

        try:
            address = 0
            with open(sys.argv[1]) as f:
                for line in f:
                    string_val = line.split("#")[0].strip()
                    if string_val == "":
                        continue
                    v = int(string_val, 2)
                    # load program into memory
                    self.ram[address] = v
                    address += 1

        except FileNotFoundError:
            print("File not found")
            sys.exit(2)

    def alu(self, op, operand_a, operand_b):
        """ALU operations."""

        if op == "ADD":
            self.reg[operand_a] += self.reg[operand_b]
        elif op == "MUL":
            self.reg[operand_a] = self.reg[operand_a] * self.reg[operand_b]
        elif op == "XOR":
            self.reg[operand_a] = self.reg[operand_a] ^ self.reg[operand_b]
        elif op == "AND":
            self.reg[operand_a] = self.reg[operand_a] & self.reg[operand_b]
        elif op == "OR":
            self.reg[operand_a] = self.reg[operand_a] | self.reg[operand_b]
        elif op == "SHR":
            self.reg[operand_a] = self.reg[operand_a] >> self.reg[operand_b]
        elif op == "SHL":
            self.reg[operand_a] = self.reg[operand_a] << self.reg[operand_b] & 0xFF
        elif op == "CMP":
            if self.reg[operand_a] == self.reg[operand_b]:
                self.fl = self.fl | 0b00000001
            else:
                self.fl = self.fl & 0b11111110

            if self.reg[operand_a] > self.reg[operand_b]:
                self.fl = self.fl | 0b00000010
            else:
                self.fl = self.fl & 0b11111101

            if self.reg[operand_a] < self.reg[operand_b]:
                self.fl = self.fl | 0b00000100
            else:
                self.fl = self.fl & 0b11111011
        else:
            raise Exception("Unsupported ALU operation")

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(
            f"TRACE: %02X | %02X %02X %02X |"
            % (
                self.pc,
                # self.fl,
                # self.ie,
                self.ram_read(self.pc),
                self.ram_read(self.pc + 1),
                self.ram_read(self.pc + 2),
            ),
            end="",
        )

        for i in range(8):
            print(" %02X" % self.reg[i], end="")

        print()

    def run(self):
        """Run the CPU.
        read the memory address that's stored in register `PC`, and store
        that result in `IR`, the _instruction_register Register_
        
        read the bytes at `PC+1` and `PC+2` from RAM into variables `operand_a` 
        and `operand_b` in case the instruction_register needs them.
        
        the `PC` needs to be updated to point to the next instruction_register 
        for the next iteration of the loop in `run()`"""

        # read the memory address that's stored in register `PC`, and store that result in `IR`
        while True:
            ir = self.ram_read(self.pc)
            if ir in self.branchtable:
                self.branchtable[ir]()

            else:
                print(f"instruction_register{hex(ir)} not recognized")
                break

    def handle_hlt(self):
        sys.exit()

    def handle_ldi(self):
        operand_a = self.ram_read(self.pc + 1)
        operand_b = self.ram_read(self.pc + 2)
        self.reg[operand_a] = operand_b
        self.pc = self.pc + 3

    def handle_st(self):
        operand_a = self.ram_read(self.pc + 1)
        operand_b = self.ram_read(self.pc + 2)
        self.ram_write(self, operand_b, operand_a)

    def handle_mul(self):
        operand_a = self.ram_read(self.pc + 1)
        operand_b = self.ram_read(self.pc + 2)
        self.alu("MUL", operand_a, operand_b)
        self.pc = self.pc + 3

    def handle_add(self):
        operand_a = self.ram_read(self.pc + 1)
        operand_b = self.ram_read(self.pc + 2)
        self.alu("ADD", operand_a, operand_b)
        self.pc = self.pc + 3

    def handle_cmp(self):
        operand_a = self.ram_read(self.pc + 1)
        operand_b = self.ram_read(self.pc + 2)
        self.alu("CMP", operand_a, operand_b)
        self.pc = self.pc + 3

    def handle_prn(self):
        operand_a = self.ram_read(self.pc + 1)
        print(self.reg[operand_a])
        self.pc = self.pc + 2

    def handle_pop(self):
        """
        Pop the value at the top of the stack into the given register.
        Copy the value from the address pointed to by SP to the given register.
        Increment SP.
        """
        operand_a = self.ram_read(self.pc + 1)
        self.reg[operand_a] = self.ram_read(self.sp + 1)
        self.sp += 1
        self.pc += 2

    def handle_push(self):
        """
        Decrement the SP.
        Copy the value in the given register to the address pointed to by SP
        """
        operand_a = self.ram_read(self.pc + 1)
        self.ram_write(self.sp, self.reg[operand_a])
        self.pc += 2
        self.sp -= 1

    def handle_call(self):
        operand_a = self.ram_read(self.pc + 1)
        self.sp -= 1
        self.ram_write(self.sp, self.pc + 2)
        self.pc = self.reg[operand_a]

    def handle_ret(self):
        self.pc = self.ram_read(self.sp)
        self.sp += 1

    def handle_jmp(self):
        """Jump to the address stored in the given register."""
        operand_a = self.ram_read(self.pc + 1)
        self.pc = self.reg[operand_a]

    def handle_st(self):
        """"""
        # operand_a = self.ram_read(self.pc + 1)
        # operand_b = self.ram_read(self.pc + 2)
        # self.ram_write(self.reg[operand_a], self.reg[operand_b])
        print("ST")

    def handle_jeq(self):
        if self.fl & 0b00000001 == 1:
            self.handle_jmp()
        else:
            self.pc += 2

    def handle_jne(self):
        if self.fl & 0b00000001 == 0:
            self.handle_jmp()
        else:
            self.pc += 2

    def handle_iret(self):

        for r in range(6, -1, -1):
            self.branchtable[POP]()

        self.fl = self.ram_read(self.sp)
        self.sp += 1
        self.pc = self.ram_read(self.sp)
        self.sp += 1

        self.fl = self.fl | 0b01000000      

    def ram_read(self, address_to_read):
        """accept the address to read and return the value stored there."""
        return self.ram[address_to_read]

    def ram_write(self, address_to_read, register_to_write_to):
        """accept a value to write, and the address to write it to."""
        self.ram[address_to_read] = register_to_write_to
