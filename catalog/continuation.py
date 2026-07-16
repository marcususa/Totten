def format_continuation(moves, start_ply=1):
    lines = []
    move_number = (start_ply + 1) // 2

    for i in range(0, len(moves), 2):

        white = moves[i]

        black = ""
        if i + 1 < len(moves):
            black = moves[i + 1]

        lines.append(f"{move_number}. {white} {black}".strip())
        move_number += 1

    return lines
