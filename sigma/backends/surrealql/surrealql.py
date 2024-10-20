from sigma.conversion.state import ConversionState
from sigma.rule import SigmaRule
from sigma.conversion.base import TextQueryBackend
from sigma.conditions import ConditionItem, ConditionAND, ConditionOR, ConditionNOT
from sigma.types import (
    SigmaCompareExpression,
    SigmaRegularExpression,
    SigmaRegularExpressionFlag,
)
import sigma
import re
from typing import ClassVar, Dict, Tuple, Pattern, List, Any, Optional

# pySigma backend for querying SurrealDB 2.0


class SurrealQLBackend(TextQueryBackend):
    """SurrealQL backend."""

    # TODO: change the token definitions according to the syntax. Delete these not supported by your backend.
    # See the pySigma documentation for further infromation:
    # https://sigmahq-pysigma.readthedocs.io/en/latest/Backends.html

    # Operator precedence: tuple of Condition{AND,OR,NOT} in order of precedence.
    # The backend generates grouping if required
    name: ClassVar[str] = "SurrealQL backend"
    formats: Dict[str, str] = {
        "default": "Plain SurrealQL queries",
    }
    precedence: ClassVar[Tuple[ConditionItem, ConditionItem, ConditionItem]] = (
        ConditionNOT,
        ConditionAND,
        ConditionOR,
    )

    parenthesize: bool = True
    group_expression: ClassVar[str] = (
        "({expr})"  # Expression for precedence override grouping as format string with {expr} placeholder
    )

    # Generated query tokens
    token_separator: str = " "  # Separator inserted between all boolean operators
    or_token: ClassVar[str] = "OR"  # Token used for OR operations
    and_token: ClassVar[str] = "AND"  # Token used for AND operations
    not_token: ClassVar[str] = "NOT"  # Token used for NOT operations
    eq_token: ClassVar[str] = "="  # Token used for equality comparison

    # String output
    ## Fields
    ### Quoting
    field_quote: ClassVar[str] = "'"  # Field quoting character
    field_quote_pattern: ClassVar[Pattern] = re.compile(
        "^[a-zA-Z0-9_]*$"
    )  # Pattern to match field names that don't need quoting
    field_quote_pattern_negation: ClassVar[bool] = (
        True  # If True, the pattern matches field names that need quoting
    )

    ## Values
    str_quote: ClassVar[str] = (
        "'"  # string quoting character (added as escaping character)
    )
    escape_char: ClassVar[str] = (
        "\\"  # Escaping character for special characters inside string
    )
    add_escaped: ClassVar[str] = (
        "\\"  # Characters quoted in addition to wildcards and string quote
    )

    ## Atm, SurrealQL does not support wildcards
    # wildcard_multi: ClassVar[str] = "%"  # Character used as multi-character wildcard
    # wildcard_single: ClassVar[str] = "_"  # Character used as single-character wildcard
    # filter_chars    : ClassVar[str] = ""      # Characters filtered

    bool_values: ClassVar[Dict[bool, str]] = (
        {  # Values to which boolean values are mapped.
            True: "TRUE",
            False: "FALSE",
        }
    )

    ## String matching operators. if none is appropriate eq_token is used.
    startswith_expression: ClassVar[str] = "string::starts_with({field},{value})"
    endswith_expression: ClassVar[str] = "string::ends_with({field},{value})"
    contains_expression: ClassVar[str] = "string::contains({field},{value})"
    wildcard_match_expression: ClassVar[str] = (
        "string::matches({field},{value})"  # Special expression if wildcards can't be matched with the eq_token operator
    )
    wildcard_match_str_expression: ClassVar[str] = "{field}=/{value}/"
    # wildcard_match_num_expression: ClassVar[str] = "{field} LIKE '%{value}%'"

    ## Regular expressions
    # Regular expression query as format string with placeholders {field}, {regex}, {flag_x} where x
    # is one of the flags shortcuts supported by Sigma (currently i, m and s) and refers to the
    # token stored in the class variable re_flags.
    re_expression: ClassVar[str] = "{field}=/{regex}/"
    re_escape_char: ClassVar[str] = ""  # Escape character used in regular expression

    re_escape: ClassVar[Tuple[str]] = ()  # List of strings that are escaped
    re_escape_escape_char: bool = True  # If True, the escape character is also escaped
    re_flag_prefix: bool = (
        True  # If True, the flags are prepended as (?x) group at the beginning of the regular expression, e.g. (?i). If this is not supported by the target, it should be set to False.
    )

    # CIDR expressions: define CIDR matching if backend has native support. Else pySigma expands
    # CIDR values into string wildcard matches.
    cidr_expression: ClassVar[Optional[str]] = (
        None  # CIDR expression query as format string with placeholders {field}, {value} (the whole CIDR value), {network} (network part only), {prefixlen} (length of network mask prefix) and {netmask} (CIDR network mask only).
    )

    # Numeric comparison operators
    compare_op_expression: ClassVar[str] = (
        "{field} {operator} {value}"  # Compare operation query as format string with placeholders {field}, {operator} and {value}
    )

    # Mapping between CompareOperators elements and strings used as replacement for {operator} in compare_op_expression
    compare_operators: ClassVar[Dict[SigmaCompareExpression.CompareOperators, str]] = {
        SigmaCompareExpression.CompareOperators.LT: "<",
        SigmaCompareExpression.CompareOperators.LTE: "<=",
        SigmaCompareExpression.CompareOperators.GT: ">",
        SigmaCompareExpression.CompareOperators.GTE: ">=",
    }

    # Expression for comparing two event fields
    field_equals_field_expression: ClassVar[Optional[str]] = (
        None  # Field comparison expression with the placeholders {field1} and {field2} corresponding to left field and right value side of Sigma detection item
    )
    field_equals_field_escaping_quoting: Tuple[bool, bool] = (
        True,
        True,
    )  # If regular field-escaping/quoting is applied to field1 and field2. A custom escaping/quoting can be implemented in the convert_condition_field_eq_field_escape_and_quote method.

    # Null/None expressions
    field_null_expression: ClassVar[str] = (
        "{field} IS NULL"  # Expression for field has null value as format string with {field} placeholder for field name
    )

    # Field existence condition expressions.
    field_exists_expression: ClassVar[str] = (
        "{field} IS NOT NONE"  # Expression for field existence as format string with {field} placeholder for field name
    )
    field_not_exists_expression: ClassVar[str] = (
        "{field} IS NONE"  # Expression for field non-existence as format string with {field} placeholder for field name. If not set, field_exists_expression is negated with boolean NOT.
    )

    # Field value in list, e.g. "field in (value list)" or "field containsall (value list)"
    # Could be implemented, but not handled for the moment
    convert_or_as_in: ClassVar[bool] = False  # Convert OR as in-expression
    convert_and_as_in: ClassVar[bool] = False  # Convert AND as in-expression
    in_expressions_allow_wildcards: ClassVar[bool] = (
        False  # Values in list can contain wildcards. If set to False (default) only plain values are converted into in-expressions.
    )

    field_in_list_expression: ClassVar[str] = (
        "{field} {op} [{list}]"  # Expression for field in list of values as format string with placeholders {field}, {op} and {list}
    )

    or_in_operator: ClassVar[str] = "IN"
    and_in_operator: ClassVar[str] = (
        "CONTAINSALL"  # Operator used to convert AND into in-expressions. Must be set if convert_and_as_in is set
    )
    list_separator: ClassVar[str] = ", "  # List element separator

    ## Value not bound to a field
    # unbound_value_str_expression : ClassVar[str] = "MATCH {value}"   # Expression for string value not bound to a field as format string with placeholder {value}
    # unbound_value_num_expression : ClassVar[str] = 'MATCH {value}'     # Expression for number value not bound to a field as format string with placeholder {value}

    # Query finalization: appending and concatenating deferred query part
    deferred_start: ClassVar[str] = (
        ""  # String used as separator between main query and deferred parts
    )
    deferred_separator: ClassVar[str] = (
        ""  # String used to join multiple deferred query parts
    )
    deferred_only_query: ClassVar[str] = (
        ""  # String used as query if final query only contains deferred expression
    )

    table = "<TABLE_NAME>"

    def finalize_query_default(
        self, rule: SigmaRule, query: str, index: int, state: ConversionState
    ) -> Any:

        # TODO : fields support will be handled with a backend option (all fields by default)
        # fields = "*" if len(rule.fields) == 0 else f"*, {', '.join(rule.fields)}"

        # TODO : table name will be handled with a backend option
        sqlite_query = f"SELECT * FROM {self.table} WHERE {query};"

        return sqlite_query

    def escape_and_quote_field(self, field_name: str) -> str:
        return field_name.replace(" ", "_")
