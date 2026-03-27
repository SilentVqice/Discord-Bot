import html

def build_transcript_html(channel_name: str, ticket_name: str, messages: list[dict]) -> str:
    message_blocks = []

    for msg in messages:
        author = html.escape(msg["author"])
        avatar = html.escape(msg.get("avatar_url", ""))
        created_at = msg["created_at"]
        content = html.escape(msg["content"]).replace("\n", "<br>")

        block = f"""
        <div class="message">
            <img class="avatar" src="{avatar}" alt="avatar">
            <div class="message-body">
                <div class="message-meta">
                    <span class="author">{author}</span>
                    <span class="time">{created_at}</span>
                </div>
                <div class="content">{content}</div>
            </div>
        </div>
        """
        message_blocks.append(block)

    joined_messages = "\n".join(message_blocks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(ticket_name)} Transcript</title>
    <style>
        body {{
            margin: 0;
            background: #111214;
            color: #e6e6e6;
            font-family: Arial, sans-serif;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 30px;
        }}
        .header {{
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid #2a2d31;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 0;
            color: #a0a0a0;
        }}
        .message {{
            display: flex;
            gap: 14px;
            padding: 14px 0;
            border-bottom: 1px solid #1d1f23;
        }}
        .avatar {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            object-fit: cover;
            background: #2a2d31;
        }}
        .message-body {{
            flex: 1;
        }}
        .message-meta {{
            display: flex;
            gap: 10px;
            align-items: baseline;
            margin-bottom: 4px;
        }}
        .author {{
            font-weight: 700;
        }}
        .time {{
            font-size: 13px;
            color: #9aa0a6;
        }}
        .content {{
            line-height: 1.5;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{html.escape(ticket_name)}</h1>
            <p>Channel: #{html.escape(channel_name)}</p>
        </div>
        {joined_messages}
    </div>
</body>
</html>
"""