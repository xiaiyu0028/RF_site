import json
import os


def main():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, 'parsed_actors_skill.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    missing = []
    empty = []

    for name, info in data.items():
        if not isinstance(info, dict):
            # Unexpected structure; count as missing
            missing.append(name)
            continue
        if 'parsed_passive_skills' not in info:
            missing.append(name)
        else:
            pps = info.get('parsed_passive_skills')
            if isinstance(pps, dict) and len(pps) == 0:
                empty.append(name)

    result = {
        'total_actors': len(data),
        'missing_field_count': len(missing),
        'missing_field_names': missing,
        'empty_field_count': len(empty),
        'empty_field_names': empty,
    }

    out_path = os.path.join(base_dir, 'missing_parsed_passive_skills.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Total actors: {result['total_actors']}")
    print(f"Missing 'parsed_passive_skills': {result['missing_field_count']}")
    print(f"Empty 'parsed_passive_skills': {result['empty_field_count']}")
    # Print a small preview to terminal
    preview_missing = ', '.join(missing[:10])
    if preview_missing:
        print(f"First missing: {preview_missing}{' ...' if len(missing) > 10 else ''}")


if __name__ == '__main__':
    main()
