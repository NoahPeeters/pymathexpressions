__author__ = 'Noah Peeters'

from enum import Enum
import copy

import mathexpressions.lib as lib


print_indent = 0


class Kind(Enum):
    K_OPERATOR = 0
    K_FUNCTION = 1
    K_CONST = 2
    K_VAR = 3
    K_BRACKET = 4


class Part:
    def __init__(self, kind, name, value, parts):
        self.name = name
        self.kind = kind
        self.value = value
        self.parts = parts

    def __str__(self):
        s = "%s: %s with value %s" % (self.kind, self.name, str(self.value))
        global print_indent
        print_indent += 1
        if self.parts is not None:
            if self.kind == Kind.K_BRACKET:
                for a in self.parts:
                    s += "\n" + "  " * print_indent + str(a)
            elif self.kind == Kind.K_FUNCTION:
                for a in self.parts:
                    for b in a:
                        s += "\n" + "  " * print_indent + str(b)
                    s += '\n'
        print_indent -= 1
        return s


class Parser:
    def __init__(self):
        self.__function = []
        self.__varNames = ['x']
        self.__varValues = [3]

    def __get_value(self, p):
        assert isinstance(p, Part)
        if p.kind == Kind.K_CONST:
            return p.value
        elif p.kind == Kind.K_VAR:
            return self.__varValues[self.__varNames.index(p.name)]
        elif p.kind == Kind.K_BRACKET:
            return self.__rec_calc_function(p.parts)
        elif p.kind == Kind.K_FUNCTION:
            para = [self.__rec_calc_function(x) for x in p.parts]
            return lib.use_function(p.name, para)
        else:
            raise Exception("Error while calculating")

    def __rec_parse_function(self, f):
        f += ' '

        tmpfunction = []
        tmp = ''
        state = 0
        functionname = ''
        bracketcounter = 0

        for cc in f:
            c = cc[0]
            if state != 0:
                if state == 2:
                    c = ''
                    state = 4
                searchforbeginning = False
                if c == '(':
                    bracketcounter += 1
                    tmp += c
                elif c == ')':
                    if bracketcounter == 0:
                        if state == 1:
                            tmpfunction.append(Part(Kind.K_BRACKET, '', 0, self.__rec_parse_function(tmp)))
                        elif state == 4:
                            tmpfunction.append(
                                Part(Kind.K_FUNCTION, functionname, 0,
                                     [self.__rec_parse_function(x) for x in tmp.split(',')]))
                        state = 0
                        tmp = ''
                    else:
                        bracketcounter -= 1
                        tmp += c
                elif state == 3 and c not in lib.floatChars:
                    tmpfunction.append(Part(Kind.K_CONST, '', float(tmp), None))
                    searchforbeginning = True
                    tmp = ''
                    state = 0
                else:
                    tmp += c
            else:
                searchforbeginning = True

            if searchforbeginning:
                tmp += c
                if tmp in self.__varNames:
                    tmpfunction.append(Part(Kind.K_VAR, tmp, 0, None))
                    tmp = ''
                elif tmp in lib.constNames:
                    tmpfunction.append(Part(Kind.K_CONST, '', lib.constValues[lib.constNames.index(tmp)], None))
                    tmp = ''
                elif tmp in lib.operators:
                    tmpfunction.append(Part(Kind.K_OPERATOR, tmp, 0, None))
                    tmp = ''
                elif tmp == '(':
                    state = 1
                    tmp = ''
                elif tmp in lib.functions:
                    functionname = tmp
                    state = 2
                    tmp = ''
                elif len(tmp) == 1 and tmp in lib.floatChars:
                    state = 3
                elif tmp == ')':
                    raise Exception(
                        "Error while reading function:" +
                        " Expect '(', operator, function, number, constant or variable but found EOF")

        print(tmp)
        if bracketcounter != 0:
            raise Exception("EOF while reading function: Expect ')' but found EOF")
        return tmpfunction

    def __rec_improve_function(self, f):
        new = copy.deepcopy(f)

        for count in range(len(new)):
            p = new[count]
            assert isinstance(p, Part)
            if p.kind == Kind.K_BRACKET:
                parts = self.__rec_improve_function(p.parts)
                if len(parts) == 1:
                    tmp_p = parts[0]
                    assert isinstance(tmp_p, Part)
                    if tmp_p.kind != Kind.K_VAR:
                        new[count] = Part(Kind.K_CONST, '', self.__get_value(tmp_p), None)
                    else:
                        new[count] = tmp_p
                else:
                    new[count] = Part(Kind.K_BRACKET, '', 0, parts)
            elif p.kind == Kind.K_FUNCTION:
                params = [self.__rec_improve_function(p.parts[x]) for x in range(len(p.parts))]
                can_resolved = True
                for count2 in range(len(params)):
                    if len(params[count2]) == 1:
                        tmp_p = params[count2][0]
                        assert isinstance(tmp_p, Part)
                        if tmp_p.kind != Kind.K_VAR:
                            params[count2] = [Part(Kind.K_CONST, '', self.__get_value(tmp_p), None)]
                        else:
                            params[count2] = [tmp_p]
                            can_resolved = False
                    else:
                        can_resolved = False
                if can_resolved:
                    new[count] = Part(Kind.K_CONST, '', self.__get_value(p), None)

        for priority in reversed(range(lib.max_priority + 1)):
            count = 0
            while count < len(new):
                p = new[count]
                assert isinstance(p, Part)
                if p.kind == Kind.K_OPERATOR and lib.get_priority(p) == priority and \
                                new[count - 1].kind == Kind.K_CONST and \
                                new[count + 1].kind == Kind.K_CONST and \
                        (count - 2 < 0 or lib.get_priority(new[count - 2]) <= priority) and \
                        (count + 2 >= len(new) or lib.get_priority(new[count + 2]) <= priority):
                    new[count - 1] = Part(Kind.K_CONST, '',
                                          lib.use_operator(p.name, new[count - 1].value, new[count + 1].value), None)
                    new.pop(count)
                    new.pop(count)
                else:
                    count += 1
        return new

    def __rec_calc_function(self, f):
        new = copy.deepcopy(f)

        for priority in reversed(range(lib.max_priority + 1)):
            count = 0
            while count < len(new):
                p = new[count]
                assert isinstance(p, Part)
                if p.kind == Kind.K_OPERATOR and lib.get_priority(p) == priority:
                    new[count - 1] = Part(Kind.K_CONST, '',
                                          lib.use_operator(p.name, self.__get_value(new[count - 1]),
                                                           self.__get_value(new[count + 1])),
                                          None)
                    new.pop(count)
                    new.pop(count)
                else:
                    count += 1

        p = new[0]
        assert isinstance(p, Part)
        return self.__get_value(p)

    def add_var(self, name, value):
        self.__varNames.append(name)
        self.__varValues.append(value)
        return True

    def edit_var(self, name, value):
        index = self.__varValues.index(name)
        if index == -1:
            return False
        else:
            self.__varValues[index] = value
            return True

    def get_var(self, name):
        index = self.__varValues.index(name)
        if index == -1:
            return None
        else:
            return self.__varValues[index]

    def parse_function(self, function):
        self.__function = self.__rec_parse_function(function)

    def improve_function(self):
        self.__function = self.__rec_improve_function(self.__function)

    def calc_function(self):
        return self.__rec_calc_function(self.__function)