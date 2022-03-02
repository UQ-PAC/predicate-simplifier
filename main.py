"""
Created by James Tobler, 2022.
A command-line tool for converting logical sentences into simplified DNF or CNF.
Converts to CNF by default.
Interprets the order of precedence: ['~', '&&', '||', '=>']
Interprets the following as logic symbols: ['&&', '||', '~', '(', ')', '=>']. Everything else is interpreted as a
term. Spaces are ignored.
Usage: main.py sentence [dnf]

Usage example 1:
> main.py 'a => b && c' dnf
~a || (b && c)

Usage example 2:
> main.py 'a => b && ~c'
(~a || ~c) && (~a || b)
"""

import itertools
import sys

# logical connectives to be recognised. warning: if modifying this list, other parts of the code should be modified
SYMBOLS = ['&&', '||', '~', '(', ')', '=>']


def main():
    sentence = sys.argv[1]  # 'a && b => a && c'
    dnf_mode = len(sys.argv) >= 3 and sys.argv[2].lower() == 'dnf'
    sentence_components = compartmentalise_sentence(sentence)  # [a, &&, b, =>, a, &&, c]
    if not is_valid_sentence(sentence_components):
        print('Invalid sentence.')
        exit(1)
    variables = extract_terms(sentence_components)  # [a, b, c]
    # the encodings of the terms as they would appear on a truth table
    term_encodings = encode_terms(variables)  # {a: 00001111, b: 00110011, c: 01010101}
    # the encoding of the sentence as it would appear on a truth table
    sentence_encoding = encode_sentence(sentence_components, term_encodings)  # 11111101
    # convert the sentence encoding into a string representing a simplified cnf or dnf form of the predicate
    output = convert_to_predicate(sentence_encoding, term_encodings, dnf_mode)
    print(output)


# LITERAL PARSING AND SENTENCE COMPONENT CREATION


def compartmentalise_sentence(sentence: str):
    """
    Converts a predicate string into a list of its terms and logical connectives.
    E.g. 'a && b => a && c' is converted to ['a', '&&', 'b', '=>', 'a', '&&', 'c'].
    :param sentence: string representing a logical sentence, to be converted.
    :return: a list of the terms and logical connectives used in the predicate, maintaining order and repetitions.
    """
    sentence_components = []
    sentence = sentence.replace(' ', '')
    current_term = ''  # gradually builds the names of terms as the sentence is parsed char by char
    i = 0
    while i < len(sentence):
        for op in SYMBOLS:
            if sentence[i:min(len(sentence), i + len(op))] == op:  # match operator without reading past the sentence
                # operator found; store the term we've built so far if it exists
                if current_term:
                    sentence_components.append(current_term)
                    current_term = ''
                sentence_components.append(op)
                i += len(op)
                break
            elif op == SYMBOLS[-1]:
                # no operator found; append this char to the term name we're building
                current_term += sentence[i]
                i += 1
    if current_term:
        sentence_components.append(current_term)
    return sentence_components


def is_valid_sentence(sentence_components: list):
    """
    Checks if the given sentence (provided as a list of its components) constitutes a valid logical sentence.
    Valid sentences satisfy the following criteria:
    1. The start, all operators and opening parentheses must precede terms, unary operators or opening parentheses.
    2. Terms and closing parentheses must precede binary operators, closing parentheses or the end.
    3. All parentheses have matching closing parentheses.
    :param sentence_components: the sentence to be checked for validity, given as a list of its components. See
    @compartmentalise_sentence.
    :return: true iff the sentence is valid.
    """
    # an empty sentence is invalid
    if not sentence_components:
        return False
    # keep track of open parentheses parsed vs closed parentheses parsed
    open_minus_closed_parens = 0
    # the start must precede terms, unary operators or opening parentheses
    if sentence_components[0] in ['&&', '||', '=>', ')']:
        return False
    for i in range(0, len(sentence_components)):
        if sentence_components[i] == '(':
            open_minus_closed_parens += 1
        elif sentence_components[i] == ')':
            open_minus_closed_parens -= 1
            if open_minus_closed_parens < 0:
                # found a closing parenthesis with no matching open parenthesis
                return False
        # these next two conditions are simplified forms of rules 1 and 2
        if sentence_components[i] in ['&&', '||', '=>', '~', '(']:
            if i + 1 == len(sentence_components) or sentence_components[i + 1] in ['&&', '||', '=>', ')']:
                return False
        else:
            if i + 1 != len(sentence_components) and sentence_components[i + 1] not in ['&&', '||', '=>', ')']:
                return False
    # check that all open parentheses have matching closed parentheses
    return open_minus_closed_parens == 0


def extract_terms(sentence_components: list):
    """
    Extracts all unique variables from a list of sentence components.
    :param sentence_components: A list of all sentence components. See @compartmentalise_sentence.
    :return: A list of all unique variables in the given list of sentence components.
    """
    variables = {i for i in sentence_components if i not in SYMBOLS}
    return list(variables)


# CONSTRUCTING TRUTH TABLES FROM SENTENCE COMPONENTS


def encode_terms(variables: list):
    """
    Constructs integers representing binary sequences of each term in the given list, similar to how they would appear
    on a truth table. For example, for variables [a, b], returns {a: 12, b: 10}, where 12 and 10
    correspond with the binary numbers 1100 and 1010 respectively.
    :param variables: The list of variables to encode.
    :return: A dictionary which maps each given variable to a unique encoding, similar to how they would be encoded in
    a truth table.
    """
    encodings = {}
    for i in range(len(variables)):
        encoding = 0
        for j in range(2 ** len(variables)):
            encoding += 2 ** j * ((j % 2 ** (i + 1)) // 2 ** i)  # just trust me
        encodings[variables[i]] = encoding
    return encodings


def encode_sentence(sentence_components: list, variable_encodings: dict):
    """
    Takes a sentence (in the form of a list of its components), and returns its encoding, in accordance with the
    given encodings of its variables. This is similar to filling out the sentence column of a truth table.
    :param sentence_components: A list containing the components of the sentence. See @compartmentalise_sentence.
    :param variable_encodings: A dictionary containing the encodings of each variable in the given sentence.
    :return: The given sentence's encoding.
    """
    # use the shunting yard algorithm to arrange the sentence in postfix form
    postfix_sentence = get_postfix_ordering(sentence_components)
    encoding = 0
    # at each row in the truth table, compute the value of the sentence and modify the sentence encoding accordingly
    for i in reversed(range(0, 2 ** len(variable_encodings))):
        evaluative_stack = []
        for symbol in postfix_sentence:
            if symbol in variable_encodings.keys():
                # term found; calculate the value of the term at this row and add to the evaluative stack
                evaluative_stack.append(variable_encodings[symbol] & 2 ** i)
            else:
                # operator found; pop the required terms from the evaluative stack and compute the operation's result
                terms = [evaluative_stack.pop()]
                if symbol != '~':
                    terms.insert(0, evaluative_stack.pop())
                evaluative_stack.append(evaluate_operation(symbol, terms))
        result = evaluative_stack.pop()
        encoding *= 2
        if result:
            encoding += 1
    return encoding


def get_postfix_ordering(sentence_components: list):
    """
    Uses the shunting yard algorithm to arrange the sentence in postfix form.
    :param sentence_components: To be arranged in postfix form.
    :return: A list of the sentence components, arranged into postfix form.
    """
    output_queue = []
    operator_stack = []
    for symbol in sentence_components:
        if symbol not in SYMBOLS:
            output_queue.append(symbol)
        elif symbol not in ['(', ')']:
            while operator_stack and get_precedence(operator_stack[-1]) > get_precedence(symbol):
                output_queue.append(operator_stack.pop())
            operator_stack.append(symbol)
        elif symbol == '(':
            operator_stack.append(symbol)
        else:
            while operator_stack[-1] != '(':
                output_queue.append(operator_stack.pop())
            operator_stack.pop()
    while operator_stack:
        output_queue.append(operator_stack.pop())
    return output_queue


def evaluate_operation(op, terms: list):
    """
    Evaluates a unary or binary expression.
    :param op: The operation or logical connective in the expression.
    :param terms: The terms in the expression, as True/False values.
    :return: The boolean result of the expression.
    """
    if op == '~':
        return not terms[0]
    elif op == '&&':
        return terms[0] and terms[1]
    elif op == '||':
        return terms[0] or terms[1]
    elif op == '=>':
        return not terms[0] or terms[1]
    print(f'Could not evaluate operator {op}')
    exit(1)


def get_precedence(operator):
    """
    Returns the precedence of the given operator / logical connective.
    :param operator: The operator to get the precedence of.
    :return: The precedence of the given operator.
    """
    if operator == '=>':
        return 1
    elif operator == '||':
        return 2
    elif operator == '&&':
        return 3
    elif operator == '~':
        return 4
    else:
        return 0


# CONVERTING TRUTH TABLES TO CNF OR DNF LOGICAL SENTENCES


def convert_to_predicate(sentence_encoding: int, variable_encodings: dict, dnf_mode: bool):
    """
    Where the magic happens. Uses the given sentence encoding and variable encodings to create a simplified list of
    simplified clauses, where each clause is a list of terms. This list of clauses can represent the DNF or CNF form
    of the given sentence encoding, depending on dnf_mode. This list of clauses is then converted into a string
    representing a logical sentence of the desired form.

    :param sentence_encoding: The encoding of the sentence to be produced as a string in CNF or DNF form, as it would
    appear on a truth table.
    :param variable_encodings: The encodings of the variables contained in the sentence, as they would appear on a truth
    table.
    :param dnf_mode: Whether the sentence encoding should be decoded into a DNF or CNF logical predicate.
    :return: A CNF or DNF logical predicate as a string, representing the given sentence encoding.
    """
    if sentence_encoding == 0:
        return 'false'
    if sentence_encoding == 2 ** (2 ** len(variable_encodings)) - 1:
        return 'true'

    clauses = []
    partial_sentence_encoding = 0 if dnf_mode else 2 ** (2 ** len(variable_encodings)) - 1
    potential_clauses = []
    clause_size = 0

    while partial_sentence_encoding != sentence_encoding:
        if not potential_clauses:
            if clause_size == len(variable_encodings):
                print('Could not find a dnf solution for the predicate.')
                exit(1)
            clause_size += 1
            potential_clauses = combination_generator(variable_encodings, clause_size, dnf_mode)
        clause, clause_code = potential_clauses.pop()
        if dnf_mode:
            if clause_code & ~partial_sentence_encoding != 0 and clause_code & ~sentence_encoding == 0:
                clauses.append(clause)
                partial_sentence_encoding |= clause_code
        else:
            if partial_sentence_encoding & ~clause_code != 0 and sentence_encoding & ~clause_code == 0:
                clauses.append(clause)
                partial_sentence_encoding &= clause_code
    sort_predicate(clauses)
    return convert_to_string(clauses, dnf_mode)


def combination_generator(variable_encodings, length, dnf_mode: bool):
    """
    Generates all combinations of the given terms, as well as their corresponding encodings, of the given length.
    For example, given the term encodings:
    {a: 00001111, b: 00110011, c: 01010101}
    ...with length=2 and dnf_mode=True, will generate:
    [([a, b], 00000011), ([a, !b], 00001100), ([!a, b], 00110000), ([!a, !b], 11000000), ([a, c], <code>),
    ([a, !c], <code>), ([!a, c], <code>), ([!a, !c], <code>), ([b, c], <code>), ([b, !c], <code>), ([!b, c], <code>),
    ([!b, !c], <code>)]

    :param variable_encodings: A dictionary mapping terms to their encodings.
    :param length: The length of the returned combinations.
    :param dnf_mode: dnf_mode=True will return the encodings for the conjunctions of each combination of terms.
    dnf_mode=False will return the encodings for the disjunctions of each combination of terms.
    :return: All combinations of the given terms, as well as their corresponding encodings, of the given length.
    """
    to_return = []
    term_combinations = itertools.combinations(variable_encodings.keys(), length)
    # [(a,b),(a,c),(b,c)] for num_terms=2
    for combination in term_combinations:
        # combination = (a,b)
        for negation_pattern in range(2 ** length):
            # negation_pattern = 01
            terms = []
            combo_code = 2 ** (2 ** len(variable_encodings)) - 1 if dnf_mode else 0
            for digit in range(length):
                # digit = 0
                term = combination[digit]  # a
                term_code = variable_encodings[term]
                if (negation_pattern >> digit) % 2:
                    term = '~' + term
                    term_code = ~term_code
                terms.append(term)
                combo_code = combo_code & term_code if dnf_mode else combo_code | term_code
            to_return.append((terms, combo_code))  # ([a, ~b], 0010)
    return to_return


def sort_predicate(predicate):
    """
    Sorts the given predicate in place. The predicate must be in the form of a list of clauses, where each clause is a
    list of terms.
    Predicates are first sorted by size (ascending), then by their clauses' terms, where terms within clauses are sorted
    alphabetically.
    :param predicate: To sort.
    """
    # sort terms within individual clauses
    for clause in predicate:
        clause.sort(key=lambda x: x.strip('~'))
    # now sort clauses according to first char of each clause
    predicate.sort(key=lambda x: x[0].strip('~'))
    # finally, sort by size
    predicate.sort(key=len)


def convert_to_string(predicate: list, dnf_mode: bool):
    """
    Converts the given predicate into a string, representing a DNF or CNF form. The predicate must be in the form of a
    list of clauses, where each clause is a list of terms. Depending on dnf_mode, the returned string will be a
    disjunction or conjunctions, or conjunction of disjunctions.
    :param predicate: To be converted to string form.
    :param dnf_mode: True iff we want to return a disjunction of conjunctions, else we return a conjunction of
    disjunctions.
    :return: A DNF or CNF logical sentence as a string, representing the given predicate.
    """
    major_separator = ' || ' if dnf_mode else ' && '
    minor_separator = ' && ' if dnf_mode else ' || '

    term_list = predicate[0]
    clause = term_list[0]
    for term in term_list[1:]:
        clause += minor_separator + term
    if len(term_list) > 1:
        # there is more than one term in this clause; add parentheses around it
        clause = '(' + clause + ')'
    to_return = clause
    for term_list in predicate[1:]:
        clause = term_list[0]
        for term in term_list[1:]:
            clause += minor_separator + term
        if len(term_list) > 1:
            # there is more than one term in this clause; add parentheses around it
            clause = '(' + clause + ')'
        to_return += major_separator + clause

    return to_return


if __name__ == '__main__':
    main()
