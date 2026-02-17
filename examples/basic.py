from __future__ import annotations

import os

import sops


def main() -> None:
    model = os.getenv("SOPS_MODEL", "gpt-5.2")
    sops.backend = sops.openai(model=model)

    print("\n--- f() plain text ---")
    answer = sops.f("What is one sentence explaining recursion?")
    print(answer)

    print("\n--- f() + o() structured object ---")
    profile = sops.f(
        "Extract a user profile from: Alice is 32, likes hiking and chess.",
        sops.o(
            {
                "name": str,
                "age": int,
                "likes": [str],
                "nickname": str | None,
            }
        ),
    )
    print(profile)

    print("\n--- c() boolean ---")
    is_true = sops.c("The capital of France is Paris.")
    print(is_true)

    print("\n--- a() typed list ---")
    primes = sops.a("Return the first five prime numbers as integers.", int)
    print(primes)


if __name__ == "__main__":
    main()
