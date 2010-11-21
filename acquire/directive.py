# Directives consist of a directive code, which broadly tells the recipient
# what the sender wishes to accomplish, and some number of parameters.
# Initialize a directive depending on how many arguments are passed in 
# and whether a sole argument appears to be in wiredata form.
import re

class Directive(object):
    """A single NetAcquire directive."""
    
    def __init__(self, *args):
        """A new directive from wiredata, if exactly one arg is given and it
        ends in `;:', or a new directive from a code and parameters, if multiple
        args are given or the lone arg does not end in `;:'.
        """
        if len(args) == 1 and args[0][-2:] == ';:':
            # Tease out the directive code and the parameters, ensuring params 
            # can be modified later.
            wiredata = args[0]
            self.code = Directive.code_regex.match(wiredata).group(0)
            self.params = Directive.parameter_regex.findall(wiredata, 
                                                            len(self.code))
            self.params = list(self.params)
        else:
            self.code, self.params = args[0], list(args[1:])
    
    # To send a directive over the wire to a NetAcquire client, just stringify 
    # it. Parameters will be escaped as needed.
    def __str__(self):
        """The wire representation of this directive.
        
        Returns a string that can be sent to a NetAcquire client.
        """
        params = list(self.params)
        if self.code == 'BM':
            params[1] = Directive.escape_param(params[1])
        elif self.code in ('GM', 'LM', 'M'):
            params[0] = Directive.escape_param(params[0])
        return "%s;%s;:" % (self.code, ','.join(str(p) for p in params))
    
    # If two directives' wiredata are identical, so are the directives.
    def __eq__(self, other):
        """Equality is done by comparing wire representations."""
        return str(self) == str(other)
    
    # Slicing a directive yields or changes its parameters.
    def __getitem__(self, key):
        """A slice of this directive's parameters."""
        return self.params[key]

    def __setitem__(self, key, val):
        """Set a slice of this directive's parameters."""
        if key == len(self.params):
            self.params.append(val)
        else:
            self.params[key] = val
    
    # NetAcquire directive parameters come surrounded with double quotes that 
    # don't get shown by clients. It's helpful to remove them when escaping or 
    # unescaping quoated parameters.
    @classmethod
    def strip_surrounding_quotes(cls, param):
        """If either the first or last characters are double quotes, ditch 
        'em.
        
        Returns a string with no starting or ending quotation marks.
        """
        param = str(param)
        if param[0] == '"':
            param = param[1:]
        if param[-1] == '"':
            param = param[:-1]
        return param
    
    # Escape a quoted parameter according to the NetAcquire protocol: 
    # doubling-up on the double quotes. `escape_param` also ensures that the 
    # escaped parameter is surrounded by double quotes.
    @classmethod
    def escape_param(cls, param):
        """Escape param by doubling-up the double quotes and then enclosing in 
        double quotes.
        
        Returns a string with doubled-up quotation marks.
        """
        return '"%s"' % cls.strip_surrounding_quotes(param).replace('"', '""')
    
    @classmethod
    def unescape_param(cls, param):
        """Reverse the effects of escape_param.
        
        Returns a string with doubled-up quotation marks now singled-up.
        """
        return cls.strip_surrounding_quotes(param).replace('""', '"')
    
    # All incoming wiredata should be processed through `parse_multiple` before 
    # being consumed. One can never assume that only one directive lies in a 
    # batch of wiredata.
    @classmethod
    def parse_multiple(cls, wiredata):
        """Extract each directive found in the wiredata.
        
        Returns a list of Directives, one for each directive found in the data.
        """
        return [cls(w) for w in Directive.regex.findall(wiredata)]
    
    # Directive codes are one or two uppercase letters.
    code_regex = r'[A-Z]{1,2}'

    # A parameter may be surrounded by double quotes. If so, any character
    # can appear in the parameter so long as double quotes are doubled-up.
    parameter_regex = r'''
        " (?: [^"] | "" )* "
    
        # Alternately, a parameter may be not surrounded by double quotes. If 
        # so, any character except double quotes, commas, semicolons, or colons 
        # is allowed.
        | [^",;:]+
    '''

    # Putting them together, a directive consists of a code and a 
    # comma-separated list of parameters, separated by a semicolon and
    # terminated by 1.5 colons.
    regex = "%s;(?: (?: (?:%s),?)*);:" % (code_regex, parameter_regex)

    # Compile these regexen for lightning-quick matches (and so we don't forget
    # the `x` modifier).
    code_regex      = re.compile(code_regex,      re.X)
    parameter_regex = re.compile(parameter_regex, re.X)
    regex           = re.compile(regex,           re.X)
