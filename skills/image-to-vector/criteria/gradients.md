# Gradient Criteria

Check:

- gradient type
- direction
- start and end points
- color stops
- opacity
- shape clipping
- target-format support

Fail if:

- gradient direction is wrong
- highlight or shadow placement shifts
- banding or harsh transitions appear
- gradient is silently dropped in a target output

If exact gradient support is unavailable, approximate visibly and document the difference.
