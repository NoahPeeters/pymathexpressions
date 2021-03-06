__author__ = 'Noah Peeters'

import copy

import mathexpressions.lib as lib


print_indent = 0


class Kind():
    K_OPERATOR = 0
    K_FUNCTION = 1
    K_CONST = 2
    K_VAR = 3
    K_BRACKET = 4
    K_LATEX = 5


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
        self.__var = {}
        self.__const = {}

    def __get_value(self, p):
        assert isinstance(p, Part)
        if p.kind == Kind.K_CONST:
            return p.value
        elif p.kind == Kind.K_VAR:
            return self.__var[p.name][0]
        elif p.kind == Kind.K_BRACKET:
            return self.__rec_calc_function(p.parts)
        elif p.kind == Kind.K_FUNCTION:
            para = [self.__rec_calc_function(x) for x in p.parts]
            return lib.use_function(p.name, para)
        else:
            raise Exception("Error while calculating")

    def __get_latex_string(self, p):
        assert isinstance(p, Part)
        if p.kind == Kind.K_CONST:
            if p.name in self.__const:
                return self.__const[p.name][1]
            elif p.name in lib.const:
                return lib.const[p.name][1]
            else:
                return p.name
        elif p.kind == Kind.K_VAR:
            return self.__var[p.name][1]
        elif p.kind == Kind.K_BRACKET:
            return '(' + self.__rec_get_latex(p.parts) + ')'
        elif p.kind == Kind.K_FUNCTION:
            para = [self.__rec_get_latex(x) for x in p.parts]
            return lib.get_function_latex(p.name, para)
        elif p.kind == Kind.K_LATEX:
            return p.name
        else:
            raise Exception("Error while calculating")

    def is_const(self, name):
        return name in self.__const or name in lib.const

    def __rec_parse_function(self, f):
        f += ' '

        tmpfunction = []
        tmp = ''
        state = 0
        functionname = ''
        bracketcounter = 0

        for c in f:
            if state != 0:
                if c == '(':
                    bracketcounter += 1
                    tmp += c
                elif c == ')':
                    if bracketcounter == 0:
                        if state == 1:
                            tmpfunction.append(Part(Kind.K_BRACKET, '', 0, self.__rec_parse_function(tmp)))
                        elif state == 2:
                            tmpfunction.append(
                                Part(Kind.K_FUNCTION, functionname, 0,
                                     [self.__rec_parse_function(x) for x in tmp.split(',')]))
                        state = 0
                        tmp = ''
                    else:
                        bracketcounter -= 1
                        tmp += c
                else:
                    tmp += c
            else:
                if c in lib.operators or c in ['(', ' ']:
                    if tmp in lib.functions:
                        functionname = tmp
                        state = 2
                    elif c == '(':
                        state = 1
                    elif tmp in self.__const:
                        tmpfunction.append(Part(Kind.K_CONST, tmp, self.__const[tmp][0], None))
                    elif tmp in lib.const:
                        tmpfunction.append(Part(Kind.K_CONST, tmp, lib.const[tmp][0], None))
                    elif lib.is_number(tmp):
                        tmpfunction.append(Part(Kind.K_CONST, tmp, float(tmp), None))
                    elif tmp.strip() != '':
                        tmpfunction.append(Part(Kind.K_VAR, tmp, 0, None))

                    tmp = ''
                    if c not in ['(', ' ']:
                        tmpfunction.append(Part(Kind.K_OPERATOR, c, 0, None))
                else:
                    tmp += c

        if tmp != '':
            raise Exception("Error while reading")
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
                        tmp = self.__get_value(tmp_p)
                        new[count] = Part(Kind.K_CONST, str(tmp), tmp, None)
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
                            tmp = self.__get_value(tmp_p)
                            params[count2] = [Part(Kind.K_CONST, str(tmp), tmp, None)]
                        else:
                            params[count2] = [tmp_p]
                            can_resolved = False
                    else:
                        can_resolved = False
                if can_resolved:
                    tmp = self.__get_value(p)
                    new[count] = Part(Kind.K_CONST, str(tmp), tmp, None)

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
                    tmp = lib.use_operator(p.name, new[count - 1].value, new[count + 1].value)
                    new[count - 1] = Part(Kind.K_CONST, str(tmp), tmp, None)
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

    def __rec_get_latex(self, f):
        new = copy.deepcopy(f)

        for priority in reversed(range(lib.max_priority + 1)):
            count = 0
            while count < len(new):
                p = new[count]
                assert isinstance(p, Part)
                if p.kind == Kind.K_OPERATOR and lib.get_priority(p) == priority:
                    new[count - 1] = Part(Kind.K_LATEX,
                                          lib.latex_operator(p.name, self.__get_latex_string(new[count - 1]),
                                                             self.__get_latex_string(new[count + 1])), 0,
                                          None)
                    new.pop(count)
                    new.pop(count)
                else:
                    count += 1

        s = ''
        for p in new:
            assert isinstance(p, Part)
            s += self.__get_latex_string(p)
        return s

    def __print(self):
        for p in self.__function:
            print(p)

    def set_const(self, lst):
        self.__const = lst

    def edit_const(self, lst):
        self.__const.update(lst)

    def remove_const(self, name):
        self.__const.pop(name, None)

    def set_var(self, lst):
        self.__var = lst

    def edit_var(self, lst):
        self.__var.update(lst)

    def remove_var(self, name):
        self.__var.pop(name, None)

    def parse_function(self, function):
        self.__function = self.__rec_parse_function(function.replace(' ', ''))

    def improve_function(self):
        self.__function = self.__rec_improve_function(self.__function)

    def calc_function(self):
        return self.__rec_calc_function(self.__function)

    def compare_function(self):
        functions = [[], []]
        c = 0
        for p in self.__function:
            assert isinstance(p, Part)
            if p.kind == Kind.K_OPERATOR and p.name == '=':
                c += 1
            else:
                functions[c].append(p)

        if c != 1:
            raise Exception("False number of '='")

        return self.__rec_calc_function(functions[0]) - self.__rec_calc_function(functions[1])

    def get_latex(self):
        return self.__rec_get_latex(self.__function)