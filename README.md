# sops
LM-native python runtime

sops (short for smart ops) is an experimental library that seamlessly embeds language models into python scripts. it's intentionally tiny and minimalistic:
it exposes `f(prompt)` for general calls and `o({...})` for structured output schemas. over these primitives, sops exposes the convenience wrappers
`c(prompt)` for conditionals and `a(prompt, type)` for typed arrays.

```python
import sops

sops.backend = sops.openai(model="gpt-5.2")

# Plain text call
answer = sops.f("What is the capital of France?")

# Structured object call
user = sops.f(
    "Extract: Alice is 32 and likes hiking and chess.",
    sops.o({"name": str, "age": int, "likes": [str], "nickname": str | None}),
)

if sops.c("The capital of France is Paris."): # Boolean helper
  primes = sops.a("Return the first 5 prime numbers.", int) # Array helper
```
