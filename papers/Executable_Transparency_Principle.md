# Executable Transparency

## Translating Mathematical Expressions into Python as a Bridge from Physical Inquiry to Formal Notation

**An Academic-Style Position Paper and Teaching Framework for the Loaded Deck Inquiry Bench**  
**Prepared May 7, 2026**

**Recovery provenance:** searchable GitHub edition derived from the surviving seven-page `Executable_Transparency_Principle_Academic_Paper.pdf`. The PDF remains preserved in the owner’s Library. This edition preserves the paper’s claims, structure, examples, guardrails, and references while normalizing page-layout artifacts.

## Abstract

This paper formalizes the **Executable Transparency Principle**: mathematical notation compresses thought, while executable code can decompress that notation into named, inspectable, and testable steps. The principle is developed from the Loaded Deck Inquiry Bench, where the binomial tail probability is translated into Python so learners can see how a formula operates before being asked to trust symbolic notation.

Code should not replace mathematical notation. It should function as a transitional representation between physical inquiry and formal expression. The method is especially useful when learners encounter summation, products, conditional logic, recursion, simulation, probability, statistics, calculus, and modeling.

**Keywords:** computational thinking; mathematical modeling; Python; binomial distribution; executable transparency; statistical inference; inquiry teaching; cognitive load

## 1. Introduction

The Loaded Deck Inquiry Bench begins with a physical experiment: students draw cards from a hidden deck, record outcomes, and infer whether the deck behaves like a fair chance machine or a loaded probability machine. The mathematical problem becomes formal when students ask how surprising an observed count would be under a stated model. For example, if 16 red cards appear in 20 replacement draws, the binomial tail probability answers the question: how often would a fair deck naturally produce 16 or more reds?

The usual formal expression is compact, efficient, and correct. Yet for many learners it is also opaque. Summation signs, binomial coefficients, exponents, and factorials compress several conceptual moves into a single line. A learner may be able to copy the formula without understanding the process it represents. The proposed teaching move is therefore: **translate the expression into visible Python before returning to the symbolic form.**

> **Central claim:** Executable code can serve as a transparent middle representation between hands-on experience and formal mathematical notation. It reveals sequence, naming, repetition, intermediate values, assumptions, and testable outputs.

## 2. Related Scholarship

The proposal is consistent with several long-standing lines of educational thought. Papert argued that computers could become objects-to-think-with, helping learners encounter powerful ideas through construction and experimentation rather than passive reception. In that spirit, executable mathematics is not merely calculation; it is a microworld in which learners can vary inputs, inspect intermediate states, debug misconceptions, and see an abstract relationship behave.

Computational-thinking scholarship supports the framing. Wing characterized computational thinking as a broadly useful way of formulating problems and solutions for an information-processing agent. Brennan and Resnick emphasized computational concepts, practices, and perspectives, including design, iteration, and artifact-based reasoning. Weintrop and colleagues proposed a taxonomy for computational thinking in mathematics and science classrooms that includes data practices, modeling and simulation, computational problem solving, and systems thinking. The Loaded Deck Inquiry Bench touches all four.

Cognitive-load theory provides another justification. Dense notation can impose extraneous load when learners must decode unfamiliar symbols while simultaneously trying to understand a new concept. Carefully written code can replace compressed symbols with meaningful names, sequence, and visible intermediate products. The purpose is not to lower intellectual demand; it is to remove unnecessary decoding burden so attention can be directed to the mathematical process.

Browser-based Python systems such as Pyodide make this practical at the laboratory table. A single web page can function as an executable mathematical instrument without requiring local Python installation.

## 3. The Executable Transparency Principle

> **Formal definition:** For many learners, a mathematical expression becomes more comprehensible when its symbolic compression is expanded into named, executable procedural steps that reveal the expression’s sequence, assumptions, intermediate values, and output behavior.

The principle does not assert that Python is superior to mathematics. It asserts that code can make the mathematics visible. Symbolic notation excels at compression, generality, and proof. Code excels at procedural revelation, inspection, iteration, and immediate feedback. A mature instructional design uses both.

| Representation | Strength | Risk if used alone |
|---|---|---|
| Physical model | Concrete, observable, memorable; supports intuition | May remain anecdotal without formal structure |
| Executable code | Shows steps, names quantities, permits testing and simulation | May become mere programming if not connected back to mathematical meaning |
| Symbolic notation | Compact, general, portable, powerful for proof | May appear authoritarian or opaque before learners understand the process |

## 4. General Formula-to-Python Translation Protocol

1. **State the physical or semantic meaning first.** Example: “This probability asks how often a fair deck would produce this many red cards or more.”
2. **Name the inputs.** Avoid single-letter variables at first when a longer name prevents ambiguity.
3. **Name the output.** State exactly what the function returns.
4. **Break the formula into conceptual parts.** Each part becomes a named variable or short helper function.
5. **Translate special notation into explicit code.** A summation becomes a loop and accumulator; a product becomes repeated multiplication; a coefficient becomes a counting function.
6. **Expose intermediate values.** Do not hide everything inside a library call during first teaching contact.
7. **Validate on small cases students can count by hand.**
8. **Reconnect the code to the symbolic notation.** The final move is not code instead of math; it is code back to math with understanding.

| Mathematical feature | Executable translation | Teaching purpose |
|---|---|---|
| Summation | `for` loop with `total = total + term` | Shows accumulation one term at a time |
| Product | Repeated multiplication or named factors | Shows what is multiplied and why |
| Binomial coefficient | `comb(n, k)` assigned to `ways` | Reveals coefficient as a count of arrangements |
| Exponent `p^k` | `p ** k` assigned to `success_part` | Links repeated success probability to repeated trials |
| Conditional expression | `if/else` with named cases | Makes domain restrictions and branching explicit |
| Integral | rectangle/trapezoid accumulation | Shows area as accumulated small pieces before formal integration |
| Derivative | finite-difference function | Shows rate of change before limit notation |
| Simulation | repeated random trials | Connects theoretical probability with empirical frequency |

## 5. Worked Example: Binomial Tail Probability

The formal question is: if the deck were fair, what is the probability of observing `k` or more red cards in `n` replacement draws?

`P(X >= k) = sum from i = k to n of [C(n, i) * p^i * (1 - p)^(n - i)]`

The expression contains four conceptual actions: choose a possible success count, count how many arrangements produce it, compute the probability of one such arrangement, and add all outcomes at least as extreme as the observation.

| Formula piece | Plain meaning | Python translation |
|---|---|---|
| `C(n, i)` | How many ways can `i` reds appear among `n` draws? | `ways = comb(n, i)` |
| `p^i` | Probability contribution from the success draws | `success_part = p ** i` |
| `(1-p)^(n-i)` | Probability contribution from remaining failures | `failure_part = (1-p) ** (n-i)` |
| sum `i=k..n` | Add exact probabilities for `k, k+1, ..., n` | loop with accumulator |

```python
from math import comb

def exact_probability(n, k, p):
    ways = comb(n, k)
    success_part = p ** k
    failure_part = (1 - p) ** (n - k)
    return ways * success_part * failure_part

def probability_at_least(n, observed_k, p):
    total = 0.0
    for k in range(observed_k, n + 1):
        total += exact_probability(n, k, p)
    return total

n = 20
observed_k = 16
p_fair = 0.50
print(probability_at_least(n, observed_k, p_fair))
```

This code is deliberately not minimized. It is written for teaching. `ways` corresponds to counting arrangements; `success_part` to repeated successes; `failure_part` to the remaining failures; the loop corresponds to the summation sign.

## 6. Why the Code Is Often More Immediately Comprehensible

For beginners, the code often reads closer to the physical action. Students understand adding one term at a time more readily than sigma notation. They understand a named variable called `ways` more readily than an unexplained binomial coefficient. They understand a loop over possible red counts more readily than compressed upper-tail notation. The code also lets them change `n`, `k`, and `p` and immediately observe consequences.

> **Instructional distinction:** The code is not easier because it is less mathematical. It is easier because it makes the mathematical process explicit.

The key abstraction is general: translate the formal expression into a transparent executable procedure; let the learner inspect and test it; then return to the formula as a compact notation for the procedure they now understand.

## 7. Generalization Across Mathematics

### 7.1 Derivatives as visible rate of change

```python
def finite_difference(f, x, h=0.001):
    change_in_y = f(x + h) - f(x)
    change_in_x = h
    return change_in_y / change_in_x
```

### 7.2 Integrals as accumulated area

```python
def rectangle_sum(f, a, b, slices=1000):
    width = (b - a) / slices
    total_area = 0.0
    for j in range(slices):
        x = a + j * width
        total_area += f(x) * width
    return total_area
```

### 7.3 Probability as repeated simulation

Before asking students to accept a theoretical distribution, simulate many experiments and compare the empirical distribution with the formula. In the Loaded Deck case, the fair-deck simulation centers around `n * 0.50`, while the loaded-deck simulation centers around `n * 0.75`.

## 8. Classroom Implementation Sequence

| Stage | Learner action | Teacher objective |
|---|---|---|
| Experience | Draw cards, record outcomes, notice patterns | Anchor probability in physical activity |
| Count | Summarize red/black and suit frequencies | Move from experience to data |
| Code | Inspect Python variables and loops | Expose the mathematical procedure |
| Simulate | Run repeated virtual experiments | Connect single trials to distributions |
| Formalize | Read the binomial expression | Compress the understood process into notation |
| Interpret | Discuss evidence, risk, and responsibility | Connect mathematics to real-world inference |

The order matters. Starting with the formula risks making the lesson feel authoritarian. Starting with experience and code lets the formula arrive as the name for something already understood.

## 9. Assessment Framework

Students have understood the principle when they can move in both directions: from formula to code and from code back to formula.

| Assessment prompt | Evidence of understanding |
|---|---|
| Explain what `comb(n, k)` means | Identifies it as the number of arrangements, not merely a calculator command |
| Point to the code corresponding to the summation sign | Identifies the loop and accumulator |
| Change `p` from 0.50 to 0.75 and predict the result | Connects `p` to deck structure and expected red count |
| Translate the Python function back into a sentence | Describes the probability question in ordinary language |
| Invent a similar translation for another formula | Generalizes the method beyond the deck activity |

## 10. Limitations and Guardrails

- Not every formula becomes clearer in Python. Simple relationships such as `V = IR` or `F = ma` may already be more readable symbolically.
- Code can become opaque if it hides the concept inside a library call. At first contact, prefer explicit named steps over compact expert code.
- Executable demonstrations should not replace proof. They support comprehension and exploration, but formal reasoning still matters.
- Preserve the assumptions. In the binomial case, replacement, stable probability, and independence are essential.
- Students should eventually learn the symbolic form. The goal is not to avoid mathematical notation but to **earn it**.

## 11. Conclusion

The Executable Transparency Principle names a practical instructional truth: code can make formal mathematics visible. In the Loaded Deck Inquiry Bench, Python exposes the binomial tail calculation as a sequence of understandable actions: count arrangements, compute success and failure probabilities, and add outcomes at least as extreme as the observed result.

This transforms a formula from an authority statement into an inspectable model. Used carefully, it provides a general method for teaching mathematical processes: begin with the physical or semantic problem, translate the process into transparent executable steps, and then return to symbolic notation as a compact, powerful summary.

## References

- Brennan, K., & Resnick, M. (2012). *New frameworks for studying and assessing the development of computational thinking.* Proceedings of the 2012 Annual Meeting of the American Educational Research Association, Vancouver, BC.
- Papert, S. (1980). *Mindstorms: Children, computers, and powerful ideas.* Basic Books.
- Pyodide Project. (2026). *Pyodide documentation: Python with the scientific stack in the browser through WebAssembly.*
- Sweller, J. (1988). “Cognitive load during problem solving: Effects on learning.” *Cognitive Science*, 12(2), 257–285.
- Weintrop, D., Beheshti, E., Horn, M. S., Orton, K., Jona, K., Trouille, L., & Wilensky, U. (2016). “Defining computational thinking for mathematics and science classrooms.” *Journal of Science Education and Technology*, 25, 127–147.
- Wing, J. M. (2006). “Computational thinking.” *Communications of the ACM*, 49(3), 33–35.
