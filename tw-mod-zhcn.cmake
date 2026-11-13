# tw-mod-zhcn: install the world migrations next to the binaries, so an install
# that runs without the source tree (such as the tortoise-deploy image, which
# reads module SQL from ${CMAKE_INSTALL_PREFIX}/modules/<module>/data/sql) still
# applies them.
if(TORTOISE_MODULE_CMAKE_PHASE STREQUAL "POST_TARGETS")
  install(DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/data/sql/world/"
    DESTINATION "${CMAKE_INSTALL_PREFIX}/modules/tw-mod-zhcn/data/sql/world")
endif()
