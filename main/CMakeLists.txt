idf_component_register(
    SRCS "main.c" "motor.c" "steering.c" "battery.c" "web.c"
    INCLUDE_DIRS "."
    EMBED_FILES "index.html"
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
