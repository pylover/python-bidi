"""Implements the level runs of the algorithm"""

from collections import deque
from chartypes import TextOrdering

class LevelRun(object):
    """Implement the level run of the alogrithm, prepending `sor` and `eor`
    to the list and setting ExChar's next and previous chars"""

    def __init__(self, sor, eor, extended_chars):
        """Prepends `sor` and appends `eor` to extended_chars"""

        self.chars = deque(extended_chars)

        # create sor and eor
        self.sor = TextOrdering(sor, next_char=self.chars[0])
        self.eor = TextOrdering(eor, prev_char=self.chars[-1])

        # update prev and next of chars
        self.chars[0].prev_char = self.sor
        self.chars[-1].next_char = self.eor

    def __repr__(self):

        return '<%s: (%s, %d %s of level %d, %s)>' % \
            (self.__class__.__name__, self.sor, len(self.chars),
            self.chars[0].__class__.__name__, self.chars[0].embed_level,
            self.eor)

    def resolve(self):
        """Apply level run resolves"""

        steps = (
            self.resolve_weak_w1_to_w3,
            self.resolve_weak_w4_to_w7,
            self.resolve_neutral,
            self.resolve_implicit_levels,
        )

        for step in steps:
            step()

    def resolve_weak_w1_to_w3(self):
        """Reslove weak type rules W1 - W3.

        See: http://unicode.org/reports/tr9/#W1

        """
        prev_strong = self.sor.bidi_type

        for ex_ch in self.chars:
            # W1. Examine each nonspacing mark (NSM) in the level run, and
            # change the type of the NSM to the type of the previous character.
            # If the NSM is at the start of the level run, it will get the type
            # of sor.
            bidi_type = ex_ch.bidi_type
            if bidi_type == 'NSM':
                ex_ch.bidi_type = bidi_type = ex_ch.prev_char.bidi_type

            # W2. Search backward from each instance of a European number until
            # the first strong type (R, L, AL, or sor) is found. If an AL is
            # found, change the type of the European number to Arabic number.
            if bidi_type == 'EN' and prev_strong == 'AL':
                ex_ch.bidi_type = 'AN'

            # update prev_strong if needed
            if bidi_type in ('R', 'L', 'AL'):
                prev_strong = bidi_type

        # W3. Change all ALs to R
        for ex_ch in self.chars:
            if ex_ch.bidi_type == 'AL':
                ex_ch.bidi_type = 'R'

    def resolve_weak_w4_to_w7(self):
        """Reslove weak type rules W4 - W7.

        See: http://unicode.org/reports/tr9/#W4

        """
        # W4. A single European separator between two European numbers changes
        # to a European number. A single common separator between two numbers of
        # the same type changes to that type.
        for ex_ch in self.chars:
            bidi_type = ex_ch.bidi_type
            prev_type = ex_ch.prev_char.bidi_type
            next_type = ex_ch.next_char.bidi_type

            if bidi_type == 'ES' and (prev_type == next_type == 'EN'):
                ex_ch.bidi_type = 'EN'

            if bidi_type == 'CS' and prev_type == next_type and \
                       prev_type in ('AN', 'EN'):
                ex_ch.bidi_type = prev_type

        # W5. A sequence of European terminators adjacent to European numbers
        # changes to all European numbers.
        for ex_ch in self.chars:
            if ex_ch.bidi_type == 'EN':
                prev_ex_ch = ex_ch.prev_char
                while prev_ex_ch and prev_ex_ch.bidi_type == 'ET':
                    prev_ex_ch.bidi_type = 'EN'
                    prev_ex_ch = prev_ex_ch.prev_char
                next_ex_ch = ex_ch.next_char
                while next_ex_ch and next_ex_ch.bidi_type == 'ET':
                    next_ex_ch.bidi_type = 'EN'
                    next_ex_ch = next_ex_ch.next_char

        # W6. Otherwise, separators and terminators change to Other Neutral.
        for ex_ch in self.chars:
            if ex_ch.bidi_type in ('ET', 'ES', 'CS'):
                ex_ch.bidi_type = 'ON'

        # W7. Search backward from each instance of a European number until the
        # first strong type (R, L, or sor) is found. If an L is found, then
        # change the type of the European number to L.
        for ex_ch in self.chars:
            if ex_ch.bidi_type == 'EN':
                prev_strong = self.sor.bidi_type

                prev_ex_ch = ex_ch.prev_char
                while prev_ex_ch:
                    if prev_ex_ch.bidi_type in ('L', 'R'):
                        prev_strong = prev_ex_ch.bidi_type
                        break
                    prev_ex_ch = prev_ex_ch.prev_char

                if prev_strong == 'L':
                    ex_ch.bidi_type = 'L'

    def resolve_neutral(self):
        """Resolving neutral types. Implements N1 and N2

        See: http://unicode.org/reports/tr9/#Resolving_Neutral_Types

        """

        for ex_ch in self.chars:
            if ex_ch.bidi_type in ('B', 'S', 'WS', 'ON'):
                # N1. A sequence of neutrals takes the direction of the
                # surrounding strong text if the text on both sides has the same
                # direction. European and Arabic numbers act as if they were R
                # in terms of their influence on neutrals. Start-of-level-run
                # (sor) and end-of-level-run (eor) are used at level run
                # boundaries.
                prev_bidi_type = ex_ch.prev_char.bidi_type
                if prev_bidi_type in ('AN', 'EN'):
                    prev_bidi_type = 'R'

                next_bidi_type = ex_ch.next_char.bidi_type
                if prev_bidi_type in ('AN', 'EN'):
                    prev_bidi_type = 'R'

                if prev_bidi_type == next_bidi_type:
                    ex_ch.bidi_type = prev_bidi_type

                # N2. Any remaining neutrals take the embedding direction. The
                # embedding direction for the given neutral character is derived
                # from its embedding level: L if the character is set to an even
                # level, and R if the level is odd.
                else:
                    ex_ch.bidi_type = ex_ch.embedding_direction

    def resolve_implicit_levels(self):
        """Resolving implicit levels (I1, I2)

        See: http://unicode.org/reports/tr9/#Resolving_Implicit_Levels

        """
        for ex_ch in self.chars:
            # only those types are allowed at this stage
            assert ex_ch.bidi_type in ('L', 'R', 'EN', 'AN')

            if ex_ch.embedding_direction == 'L':
                # I1. For all characters with an even (left-to-right) embedding
                # direction, those of type R go up one level and those of type
                # AN or EN go up two levels.
                if ex_ch.bidi_type == 'R':
                    ex_ch.embed_level += 1
                elif ex_ch.bidi_type != 'L':
                    ex_ch.embed_level += 2
            else:
                # I2. For all characters with an odd (right-to-left) embedding
                # direction, those of type L, EN or AN  go up one level.
                if ex_ch.bidi_type != 'R':
                    ex_ch.embed_level += 1
