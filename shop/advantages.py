def generate_advantages(model, *, name, category, material, size, weight):
    lines = model(
        name=name,
        category=category,
        material=material,
        size=size,
        weight=weight,
    )
    lines = [str(line).strip() for line in lines]
    if len(lines) != 4 or any(not line for line in lines):
        raise ValueError("advantages")
    return lines
