from groq import AuthenticationError, Groq, NotFoundError

from app.core.config import settings


class GroqConfigError(Exception):
    pass

def get_groq_response(prompt):
    api_key = settings.GROQ_API_KEY
    model = settings.GROQ_MODEL

    if not api_key:
        raise GroqConfigError("GROQ_API_KEY is missing. Add it to your .env file.")

    client = Groq(
        api_key=api_key
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer strictly from the supplied document context. "
                        "If the answer is not in the context, say that it could "
                        "not be found in the provided document."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
    except AuthenticationError as e:
        raise GroqConfigError(
            "Invalid or expired GROQ_API_KEY. Create a new Groq API key, "
            "update your .env file, and restart the FastAPI server."
        ) from e
    except NotFoundError as e:
        raise GroqConfigError(
            f"Groq model '{model}' was not found or is not available to your account. "
            "Set GROQ_MODEL=openai/gpt-oss-120b in your .env file, then restart "
            "the FastAPI server."
        ) from e

    return response.choices[0].message.content
