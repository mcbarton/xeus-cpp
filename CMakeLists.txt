#############################################################################
# Copyright (c) 2023, xeus-cpp contributors                                 #
#                                                                           #
# Distributed under the terms of the BSD 3-Clause License.                  #
#                                                                           #
# The full license is in the file LICENSE, distributed with this software.  #
#############################################################################

cmake_minimum_required(VERSION 3.24)
project(xeus-cpp)

enable_language(CXX)
set(CMAKE_CXX_EXTENSIONS NO)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED TRUE)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

include(GNUInstallDirs)

set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake;${CMAKE_MODULE_PATH}")

set(XEUS_CPP_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include)

# xeus-cpp tag files
set(XEUS_CPP_DATA_DIR "share/xeus-cpp")
set(XCPP_TAGFILES_DIR ${CMAKE_CURRENT_SOURCE_DIR}/share/xeus-cpp/tagfiles)

set(XEUS_CPP_CONF_DIR "etc/xeus-cpp")
set(XCPP_TAGCONFS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/etc/xeus-cpp/tags.d)

file(COPY "${XCPP_TAGFILES_DIR}" DESTINATION "${CMAKE_CURRENT_BINARY_DIR}/share/xeus-cpp")
file(COPY "${XCPP_TAGCONFS_DIR}" DESTINATION "${CMAKE_CURRENT_BINARY_DIR}/etc/xeus-cpp")

# Versionning
# ===========

file(STRINGS "${XEUS_CPP_INCLUDE_DIR}/xeus-cpp/xeus_cpp_config.hpp" version_defines
     REGEX "#define XEUS_CPP_VERSION_(MAJOR|MINOR|PATCH|LABEL)")
foreach (ver ${version_defines})
    if (ver MATCHES "#define XEUS_CPP_VERSION_(MAJOR|MINOR|PATCH|LABEL) +([^ ]+)$")
        set(XEUS_CPP_VERSION_${CMAKE_MATCH_1} "${CMAKE_MATCH_2}" CACHE INTERNAL "")
    endif ()
endforeach ()
set(${PROJECT_NAME}_VERSION
    ${XEUS_CPP_VERSION_MAJOR}.${XEUS_CPP_VERSION_MINOR}.${XEUS_CPP_VERSION_PATCH}${XEUS_CPP_VERSION_LABEL})
message(STATUS "Building xeus-cpp v${${PROJECT_NAME}_VERSION}")

# Build options
# =============

option(XEUS_CPP_BUILD_STATIC "Build xeus-cpp static library" ON)
OPTION(XEUS_CPP_BUILD_SHARED "Split xcpp build into executable and library" ON)
OPTION(XEUS_CPP_BUILD_EXECUTABLE "Build the xcpp executable" ON)

OPTION(XEUS_CPP_USE_SHARED_XEUS "Link xcpp  with the xeus shared library (instead of the static library)" ON)
OPTION(XEUS_CPP_USE_SHARED_XEUS_CPP "Link xcpp  with the xeus shared library (instead of the static library)" ON)

# Test options
OPTION(XEUS_CPP_BUILD_TESTS "xeus-cpp test suite" ON)
OPTION(XEUS_CPP_ENABLE_CODE_COVERAGE "xeus-cpp test suite" OFF)
if(XEUS_CPP_ENABLE_CODE_COVERAGE AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  string(TOUPPER "${CMAKE_BUILD_TYPE}" uppercase_CMAKE_BUILD_TYPE)
  if(NOT uppercase_CMAKE_BUILD_TYPE STREQUAL "DEBUG")
    message(FATAL_ERROR "CodeCov enabled on non-debug build!")
  endif()
  set(GCC_COVERAGE_COMPILE_FLAGS "-fprofile-arcs -ftest-coverage")
  set(GCC_COVERAGE_LINK_FLAGS    "--coverage")
  set(CMAKE_CXX_FLAGS            "${CMAKE_CXX_FLAGS} ${GCC_COVERAGE_COMPILE_FLAGS}")
  set(CMAKE_EXE_LINKER_FLAGS     "${CMAKE_EXE_LINKER_FLAGS} ${GCC_COVERAGE_LINK_FLAGS}")
  set(CMAKE_SHARED_LINKER_FLAGS  "${CMAKE_SHAREDLINKER_FLAGS} ${GCC_COVERAGE_LINK_FLAGS}")
  set(CMAKE_SHARED_LIBRARY_CREATE_CXX_FLAGS "${CMAKE_SHARED_LIBRARY_CREATE_CXX_FLAGS} ${GCC_COVERAGE_COMPILE_FLAGS}")
endif()

if(EMSCRIPTEN)
    add_compile_definitions(XEUS_CPP_EMSCRIPTEN_WASM_BUILD)
    message("Build with emscripten")
    SET(XEUS_CPP_BUILD_STATIC ON)
    SET(XEUS_CPP_BUILD_SHARED OFF)
    SET(XEUS_CPP_BUILD_EXECUTABLE OFF)
    SET(XEUS_CPP_USE_SHARED_XEUS OFF)
    SET(XEUS_CPP_USE_SHARED_XEUS_CPP OFF)
    SET(XEUS_CPP_BUILD_TESTS OFF)
endif()


# Dependencies
# ============

set(xeus_REQUIRED_VERSION 5.0.0)
set(xeus_zmq_REQUIRED_VERSION 3.0.0)

if (NOT TARGET xeus AND NOT TARGET xeus-static)
    find_package(xeus ${xeus_REQUIRED_VERSION} REQUIRED)
    if (xeus_FOUND)
        message(STATUS "Found compatible xeus version: ${xeus_VERSION}")
    endif()
endif ()

set(CppInterOp_REQUIRED_VERSION 1.3.0)

# Flags
# =====
include(CheckCXXCompilerFlag)

if (MSVC)
  add_compile_options(/wd4251 /wd4141)
  add_compile_options(/wd4018 /wd4267 /wd4715 /wd4146 /wd4129)
  add_compile_options(/EHsc)
else()
  add_compile_options(-fexceptions)
endif ()

if (CMAKE_CXX_COMPILER_ID MATCHES "Clang" OR CMAKE_CXX_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES "Intel")
    if(NOT EMSCRIPTEN)
        add_compile_options(-Wunused-parameter -Wextra -Wreorder)
    endif()
endif ()

if(EMSCRIPTEN)
    # ENV (https://github.com/emscripten-core/emscripten/commit/6d9681ad04f60b41ef6345ab06c29bbc9eeb84e0)
    set(EMSCRIPTEN_FEATURES "${EMSCRIPTEN_FEATURES} -s \"EXTRA_EXPORTED_RUNTIME_METHODS=[ENV']\"")
endif()

find_package(CppInterOp ${CppInterOp_REQUIRED_VERSION} REQUIRED)
if(CppInterOp_FOUND)
  message(STATUS "Found CppInterOp: config=${CPPINTEROP_CONFIG} dir=${CPPINTEROP_DIR} (found version=${CPPINTEROP_VERSION} compatible with Clang ${CPPINTEROP_LLVM_VERSION_MAJOR}.x)")
endif()

find_package(argparse REQUIRED)
find_package(pugixml REQUIRED)

# Configuration
# =============

if (NOT DEFINED XEUS_CPP_KERNELSPEC_PATH)
    set(XEUS_CPP_KERNELSPEC_PATH "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_BINDIR}/")
endif ()

function(configure_kernel kernel)
  set(XEUS_CPP_PATH "$ENV{PATH}")
  set(XEUS_CPP_LD_LIBRARY_PATH "$ENV{LD_LIBRARY_PATH}")
  set(XEUS_CPP_RESOURCE_DIR ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/clang/${CPPINTEROP_LLVM_VERSION_MAJOR})
  set(XEUS_CPP_INCLUDE_DIR ${CMAKE_INSTALL_PREFIX}/include)

  if (WIN32)
    string(REPLACE "\\" "/" kernel "${kernel}")
    string(REPLACE "\\" "/" XEUS_CPP_PATH "${XEUS_CPP_PATH}")
    string(REPLACE "\\" "/" XEUS_CPP_LD_LIBRARY_PATH "${XEUS_CPP_LD_LIBRARY_PATH}")
    string(REPLACE "\\" "/" XEUS_CPP_RESOURCE_DIR "${XEUS_CPP_RESOURCE_DIR}")
    string(REPLACE "\\" "/" XEUS_CPP_INCLUDE_DIR "${XEUS_CPP_INCLUDE_DIR}")
  endif()

  configure_file (
    "${CMAKE_CURRENT_SOURCE_DIR}${kernel}kernel.json.in"
    "${CMAKE_CURRENT_BINARY_DIR}${kernel}kernel.json")

  configure_file (
    "${CMAKE_CURRENT_SOURCE_DIR}${kernel}logo-32x32.png"
    "${CMAKE_CURRENT_BINARY_DIR}${kernel}"
    COPYONLY)
  configure_file (
    "${CMAKE_CURRENT_SOURCE_DIR}${kernel}logo-64x64.png"
    "${CMAKE_CURRENT_BINARY_DIR}${kernel}"
    COPYONLY)
  configure_file (
    "${CMAKE_CURRENT_SOURCE_DIR}${kernel}logo-svg.svg"
    "${CMAKE_CURRENT_BINARY_DIR}${kernel}"
    COPYONLY)
endfunction()

message("Configure kernels: ...")
configure_kernel("/share/jupyter/kernels/xcpp17/")
configure_kernel("/share/jupyter/kernels/xcpp20/")

# Source files
# ============

set(XEUS_CPP_HEADERS
    include/xeus-cpp/xbuffer.hpp
    include/xeus-cpp/xholder.hpp
    include/xeus-cpp/xoptions.hpp
    include/xeus-cpp/xeus_cpp_config.hpp
    include/xeus-cpp/xholder.hpp
    include/xeus-cpp/xinterpreter.hpp
    include/xeus-cpp/xmanager.hpp
    include/xeus-cpp/xmagics.hpp
    include/xeus-cpp/xoptions.hpp
    include/xeus-cpp/xpreamble.hpp
    #src/xdemangle.hpp
    #src/xinspect.hpp
    #src/xsystem.hpp
    #src/xparser.hpp
    #src/xmagics/os.hpp
)

set(XEUS_CPP_SRC
    src/xholder.cpp
    src/xinput.cpp
    src/xinterpreter.cpp
    src/xmagics/os.cpp
    src/xoptions.cpp
    src/xparser.cpp
    src/xutils.cpp
)

if(EMSCRIPTEN)
    list(APPEND XEUS_CPP_SRC src/xinterpreter_wasm.cpp)
endif()

set(XEUS_CPP_MAIN_SRC
    src/main.cpp
)

# Targets and link - Macros
# =========================

include(CheckCXXCompilerFlag)

string(TOUPPER "${CMAKE_BUILD_TYPE}" U_CMAKE_BUILD_TYPE)

set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib;${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}")
list(REMOVE_DUPLICATES CMAKE_INSTALL_RPATH)

macro(xeus_cpp_set_common_options target_name)
    if (MSVC)
        target_compile_options(${target_name} PUBLIC /wd4251 /wd4141)
        target_compile_options(${target_name} PUBLIC /wd4018 /wd4267 /wd4715 /wd4146 /wd4129)
    endif ()

    if (CMAKE_CXX_COMPILER_ID MATCHES "Clang" OR
        CMAKE_CXX_COMPILER_ID MATCHES "GNU" OR
        CMAKE_CXX_COMPILER_ID MATCHES "Intel")

        target_compile_options(${target_name} PUBLIC -Wunused-parameter -Wextra -Wreorder)

        # C++17 flag
        CHECK_CXX_COMPILER_FLAG("-std=c++17" HAS_CPP_17_FLAG)
        if (HAS_CPP_17_FLAG)
            target_compile_features(${target_name} PRIVATE cxx_std_17)
        else ()
            message(FATAL_ERROR "Unsupported compiler -- xeus-cpp requires C++17 support!")
        endif ()
    endif ()

    if (APPLE)
        set_target_properties(${target_name} PROPERTIES
            MACOSX_RPATH ON
        )
    else ()
        set_target_properties(${target_name} PROPERTIES
            BUILD_WITH_INSTALL_RPATH 1
            SKIP_BUILD_RPATH FALSE
        )
    endif ()

    set_target_properties(${target_name} PROPERTIES
        INSTALL_RPATH_USE_LINK_PATH TRUE
    )
endmacro()

# Common macro kernels (xcpp)
macro(xeus_cpp_set_kernel_options target_name)
    if (XEUS_CPP_USE_SHARED_XEUS_CPP)
        target_link_libraries(${target_name} PRIVATE xeus-cpp)
        if(CMAKE_DL_LIBS)
            target_link_libraries(${target_name} PRIVATE ${CMAKE_DL_LIBS} util)
        endif()
    else ()
        target_link_libraries(${target_name} PRIVATE xeus-cpp-static)
    endif()

    if(NOT EMSCRIPTEN)
        find_package(Threads)
        target_link_libraries(${target_name} PRIVATE ${CMAKE_THREAD_LIBS_INIT})
    endif()
endmacro()

# Common macro for shared and static library
macro(xeus_cpp_create_target target_name linkage output_name)
    string(TOUPPER "${linkage}" linkage_upper)

    if (NOT ${linkage_upper} MATCHES "^(SHARED|STATIC)$")
        message(FATAL_ERROR "Invalid library linkage: ${linkage}")
    endif ()

    add_library(${target_name} ${linkage_upper} ${XEUS_CPP_SRC} ${XEUS_CPP_HEADERS})
    xeus_cpp_set_common_options(${target_name})

    set_target_properties(${target_name} PROPERTIES
                          PUBLIC_HEADER "${XEUS_CPP_HEADERS}"
                          PREFIX ""
                          VERSION ${${PROJECT_NAME}_VERSION}
                          SOVERSION ${XEUS_CPP_VERSION_MAJOR}
                          OUTPUT_NAME "lib${output_name}")

    target_compile_definitions(${target_name} PUBLIC "XEUS_CPP_EXPORTS")

    target_compile_features(${target_name} PRIVATE cxx_std_17)

    target_include_directories(${target_name}
                               PUBLIC
                               $<BUILD_INTERFACE:${XEUS_CPP_INCLUDE_DIR}>
                               $<INSTALL_INTERFACE:include>)

    if (XEUS_CPP_USE_SHARED_XEUS)
        set(XEUS_CPP_XEUS_TARGET xeus)
    else ()
        set(XEUS_CPP_XEUS_TARGET xeus-static)
    endif ()

    target_link_libraries(${target_name} PUBLIC ${XEUS_CPP_XEUS_TARGET} clangCppInterOp pugixml argparse::argparse)

    if (WIN32 OR CYGWIN)
        #
    elseif (APPLE)
        target_link_libraries(${target_name} PRIVATE "-undefined dynamic_lookup")
    endif ()
    if(NOT EMSCRIPTEN)
        find_package(Threads) # TODO: add Threads as a dependence of xeus-static?
        target_link_libraries(${target_name} PRIVATE ${CMAKE_THREAD_LIBS_INIT})
    endif()

endmacro()

# xeus-cpp-headers
# ================

set(XCPP_HEADERS
    include/xcpp/xmime.hpp
    include/xcpp/xdisplay.hpp
)
add_library(xeus-cpp-headers INTERFACE)
set_target_properties(xeus-cpp-headers PROPERTIES PUBLIC_HEADER "${XCPP_HEADERS}")

install(TARGETS xeus-cpp-headers PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/xcpp)

# xeus-cpp
# ========

set(XEUS_CPP_TARGETS "")

if (XEUS_CPP_BUILD_SHARED)
    # Build libraries
    xeus_cpp_create_target(xeus-cpp SHARED xeus-cpp)
    list(APPEND XEUS_CPP_TARGETS xeus-cpp)
endif ()

if (XEUS_CPP_BUILD_STATIC)
    # On Windows, a static library should use a different output name
    # to avoid the conflict with the import library of a shared one.
    if (CMAKE_HOST_WIN32)
        xeus_cpp_create_target(xeus-cpp-static STATIC xeus-cpp-static)
    else ()
        xeus_cpp_create_target(xeus-cpp-static STATIC xeus-cpp)
    endif ()
    list(APPEND XEUS_CPP_TARGETS xeus-cpp-static)
endif ()

# xcpp
# ====

if (XEUS_CPP_BUILD_EXECUTABLE)
    find_package(xeus-zmq ${xeus_zmq_REQUIRED_VERSION} REQUIRED)
    add_executable(xcpp ${XEUS_CPP_MAIN_SRC})
    target_compile_features(xcpp PRIVATE cxx_std_17)
    xeus_cpp_set_common_options(xcpp)
    xeus_cpp_set_kernel_options(xcpp)
    target_link_libraries(xcpp PRIVATE xeus-zmq)
endif()

if(EMSCRIPTEN)
    include(WasmBuildOptions)
    find_package(xeus-lite REQUIRED)
    add_executable(xcpp src/main_emscripten_kernel.cpp )
    target_link_libraries(xcpp PRIVATE xeus-lite)
    xeus_cpp_set_kernel_options(xcpp)
    xeus_wasm_compile_options(xcpp)
    xeus_wasm_link_options(xcpp "web,worker")
endif()

if(MSVC)

    set_target_properties(xeus-cpp PROPERTIES
                      PUBLIC_HEADER "${XEUS_CPP_HEADERS}"
                      COMPILE_DEFINITIONS "XEUS_CPP_EXPORTS"
                      PREFIX ""
                      VERSION ${${PROJECT_NAME}_VERSION}
                      SOVERSION ${XEUS_CPP_VERSION_MAJOR}
                      OUTPUT_NAME "libxeus-cpp")

    set_target_properties(xeus-cpp PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS 1)  # Internal string
    # RTTI/C++ symbols
    set(xeus_cpp_exports ??_7type_info@@6B@
        ?__type_info_root_node@@3U__type_info_node@@A
        ?nothrow@std@@3Unothrow_t@1@B
        ?_Facet_Register@std@@YAXPEAV_Facet_base@1@@Z
    )

    # Compiler added symbols for static variables. NOT for VStudio < 2015
    set(xeus_cpp_exports ${xeus_cpp_exports} _Init_thread_abort _Init_thread_epoch
        _Init_thread_footer _Init_thread_header _tls_index
    )

    # new/delete variants needed when linking to static msvc runtime (esp. Debug)
    set(xeus_cpp_exports ${xeus_cpp_exports}
        ??2@YAPEAX_K@Z
        ??3@YAXPEAX@Z
        ??3@YAXPEAX_K@Z
        ??_U@YAPEAX_K@Z
        ??_V@YAXPEAX@Z
    )

    # Most (if not all) of these MSVC decided are inlines that aren't exported
    # TODO: There are probably some missing. Why?
    set(xeus_cpp_exports ${xeus_cpp_exports} ?print@Decl@clang@@QEBAXAEAVraw_ostream@llvm@@I_N@Z
        ??6raw_ostream@llvm@@QEAAAEAV01@PEBX@Z
        ?decls_begin@DeclContext@clang@@QEBA?AVdecl_iterator@12@XZ
        ?errs@llvm@@YAAEAVraw_ostream@1@XZ
        ?grow_pod@SmallVectorBase@llvm@@IEAAXPEAX_K1@Z
        ?write@raw_ostream@llvm@@QEAAAEAV12@E@Z
        ?write@raw_ostream@llvm@@QEAAAEAV12@PEBD_K@Z
        ?castFromDeclContext@Decl@clang@@SAPEAV12@PEBVDeclContext@2@@Z
        ??1raw_ostream@llvm@@UEAA@XZ
        ??1raw_string_ostream@llvm@@UEAA@XZ
        ?flush_nonempty@raw_ostream@llvm@@AEAAXXZ
        ?getASTContext@Decl@clang@@QEBAAEAVASTContext@2@XZ
        ?preferred_buffer_size@raw_ostream@llvm@@MEBA_KXZ
        ?write_impl@raw_string_ostream@llvm@@EEAAXPEBD_K@Z
        ?castToDeclContext@Decl@clang@@SAPEAVDeclContext@2@PEBV12@@Z
        ?classof@DeclContext@clang@@SA_NPEBVDecl@2@@Z    )

set(xeus_cpp_exports ${xeus_cpp_exports} ??$?6U?$char_traits@D@std@@@std@@YAAEAV?$basic_ostream@DU?$char_traits@D@std@@@0@AEAV10@PEBD@Z 
__orc_init_func.incr_module_4
$.incr_module_4.__inits.0
??0_System_error@std@@QEAA@AEBV01@@Z
 ?assign@?$_Narrow_char_traits@DH@std@@SAXAEADAEBD@Z
 ??$_Bit_cast@_KT_Addr_storage@error_category@std@@$0A@@std@@YA_KAEBT_Addr_storage@error_category@0@@Z
 ?default_error_condition@error_category@std@@UEBA?AVerror_condition@2@H@Z
 ??_7_Iostream_error_category2@std@@6B@
 ?flags@ios_base@std@@QEBAHXZ
 ??_R2_Crt_new_delete@std@@8
 ??_R2system_error@std@@8
 ??0_Fake_proxy_ptr_impl@std@@QEAA@AEBU_Fake_allocator@1@AEBU_Container_base0@1@@Z
 _CT??_R0?AVbad_cast@std@@@8??0bad_cast@std@@QEAA@AEBV01@@Z24
 ??0bad_array_new_length@std@@QEAA@AEBV01@@Z
 ?_Iostream_error@?4??message@_Iostream_error_category2@std@@UEBA?AV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@3@H@Z@4QBDB
 ??$_Unfancy@D@std@@YAPEADPEAD@Z
 ??_7bad_array_new_length@std@@6B@
 ??_R3exception@std@@8
 ??_7bad_cast@std@@6B@
 ?eq_int_type@?$_Narrow_char_traits@DH@std@@SA_NHH@Z
 ?deallocate@?$allocator@D@std@@QEAAXQEAD_K@Z
 ??_Gfailure@ios_base@std@@UEAAPEAXI@Z
 ?release@?$unique_ptr@V_Facet_base@std@@U?$default_delete@V_Facet_base@std@@@2@@std@@QEAAPEAV_Facet_base@2@XZ
 ?value@error_code@std@@QEBAHXZ
 ?iostream_category@std@@YAAEBVerror_category@1@XZ
 ??$_Allocate_at_least_helper@V?$allocator@D@std@@@std@@YAPEADAEAV?$allocator@D@0@AEA_K@Z
 ??0exception@std@@QEAA@AEBV01@@Z
 ??$?6U?$char_traits@D@std@@@std@@YAAEAV?$basic_ostream@DU?$char_traits@D@std@@@0@AEAV10@PEBD@Z
 ??$_Allocate@$0BA@U_Default_allocate_traits@std@@@std@@YAPEAX_K@Z
 ??1?$_String_val@U?$_Simple_types@D@std@@@std@@QEAA@XZ
 ??_R2bad_alloc@std@@8
 ?select_on_container_copy_construction@?$_Default_allocator_traits@V?$allocator@D@std@@@std@@SA?AV?$allocator@D@2@AEBV32@@Z
 ??8std@@YA_NAEBVerror_condition@0@0@Z
 ??_R17?0A@EA@_Crt_new_delete@std@@8
 ??_7facet@locale@std@@6B@
 ?category@error_code@std@@QEBAAEBVerror_category@2@XZ
 ??1_System_error@std@@UEAA@XZ
 ?_Myptr@?$_String_val@U?$_Simple_types@D@std@@@std@@QEBAPEBDXZ
 ??1system_error@std@@UEAA@XZ
 _CT??_R0?AVsystem_error@std@@@8??0system_error@std@@QEAA@AEBV01@@Z40
 ??0exception@std@@QEAA@QEBD@Z
 _CT??_R0?AVbad_array_new_length@std@@@8??0bad_array_new_length@std@@QEAA@AEBV01@@Z24
 ??Bid@locale@std@@QEAA_KXZ
 ?category@error_condition@std@@QEBAAEBVerror_category@2@XZ
 ?_Throw_bad_array_new_length@std@@YAXXZ
 ??_C@_0BF@OOHOMBOF@ios_base?3?3eofbit?5set?$AA@
 ??$_Convert_size@_K_K@std@@YA_K_K@Z
 ??0bad_alloc@std@@QEAA@AEBV01@@Z
 ?what@exception@std@@UEBAPEBDXZ
 ?append@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAAAEAV12@AEBV12@@Z
 ?_Activate_SSO_buffer@?$_String_val@U?$_Simple_types@D@std@@@std@@QEAAXXZ
 ??_C@_0BA@ELKIONDK@bad?5locale?5name?$AA@
 ??_R4bad_alloc@std@@6B@
 ??_Gbad_array_new_length@std@@UEAAPEAXI@Z
 ?rdstate@ios_base@std@@QEBAHXZ
 ?put@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAAAEAV12@D@Z
 ?equivalent@error_category@std@@UEBA_NAEBVerror_code@2@H@Z
 ??$min@_K@std@@YAAEB_KAEB_K0@Z
 ??0system_error@std@@QEAA@AEBV01@@Z
 ?_Getal@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAAAEAV?$allocator@D@2@XZ
 ??1_Iostream_error_category2@std@@UEAA@XZ
 ?value@error_condition@std@@QEBAHXZ
 ??0bad_alloc@std@@AEAA@QEBD@Z
 ?name@_Iostream_error_category2@std@@UEBAPEBDXZ
 ??_C@_0BF@KINCDENJ@bad?5array?5new?5length?$AA@
 ?_Alloc_proxy@_Container_base0@std@@QEAAXAEBU_Fake_allocator@2@@Z
 ??$_Deallocate@$0BA@@std@@YAXPEAX_K@Z
 ??0?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAA@$$QEAV01@@Z
 ??1exception@std@@UEAA@XZ
 _CT??_R0?AV_System_error@std@@@8??0_System_error@std@@QEAA@AEBV01@@Z40
 ??_R4facet@locale@std@@6B@
 ??0system_error@std@@QEAA@Verror_code@1@PEBD@Z
 ?append@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAAAEAV12@QEBD_K@Z
 ?getloc@ios_base@std@@QEBA?AVlocale@2@XZ
 ?_Get_first@?$_Compressed_pair@U?$default_delete@V_Facet_base@std@@@std@@PEAV_Facet_base@2@$00@std@@QEAAAEAU?$default_delete@V_Facet_base@std@@@2@XZ
 ?widen@?$ctype@D@std@@QEBADD@Z
 ??$_Adl_verify_range@PEBDPEBD@std@@YAXAEBQEBD0@Z
 _CT??_R0?AVexception@std@@@8??0exception@std@@QEAA@AEBV01@@Z24
 ?_Osfx@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAAXXZ
 _CT??_R0?AVfailure@ios_base@std@@@8??0failure@ios_base@std@@QEAA@AEBV012@@Z40
 ??1bad_array_new_length@std@@UEAA@XZ
 ?_Release@_Fake_proxy_ptr_impl@std@@QEAAXXZ
 ??1bad_alloc@std@@UEAA@XZ
 ?_Psave@?$_Facetptr@V?$ctype@D@std@@@std@@2PEBVfacet@locale@2@EB
 ??$use_facet@V?$ctype@D@std@@@std@@YAAEBV?$ctype@D@0@AEBVlocale@0@@Z
 ?make_error_code@std@@YA?AVerror_code@1@W4io_errc@1@@Z
 ?max_size@?$_Default_allocator_traits@V?$allocator@D@std@@@std@@SA_KAEBV?$allocator@D@2@@Z
 ?max_size@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEBA_KXZ
 ??1locale@std@@QEAA@XZ
 ?fill@?$basic_ios@DU?$char_traits@D@std@@@std@@QEBADXZ
 ??$_Immortalize_memcpy_image@V_Iostream_error_category2@std@@@std@@YAAEBV_Iostream_error_category2@0@XZ
 ??_7_System_error@std@@6B@
 ??0error_code@std@@QEAA@HAEBVerror_category@1@@Z
 ?_Switch_to_buf@_Bxty@?$_String_val@U?$_Simple_types@D@std@@@std@@QEAAXXZ
 ?sputc@?$basic_streambuf@DU?$char_traits@D@std@@@std@@QEAAHD@Z
 ??_R1A@?0A@EA@error_category@std@@8
 ?allocate@?$allocator@D@std@@QEAAPEAD_K@Z
 ??_G_System_error@std@@UEAAPEAXI@Z
 ?_Allocate@_Default_allocate_traits@std@@SAPEAX_K@Z
 ?_Pnavail@?$basic_streambuf@DU?$char_traits@D@std@@@std@@IEBA_JXZ
 ??_R0?AVruntime_error@std@@@8
 ??0runtime_error@std@@QEAA@AEBV01@@Z
 ??R?$default_delete@V_Facet_base@std@@@std@@QEBAXPEAV_Facet_base@1@@Z
 ?_Adjust_manually_vector_aligned@std@@YAXAEAPEAXAEA_K@Z
 ?_Getal@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEBAAEBV?$allocator@D@2@XZ
 ??1runtime_error@std@@UEAA@XZ
 ?_Orphan_all@_Container_base0@std@@QEAAXXZ
 ?_Getcat@?$ctype@D@std@@SA_KPEAPEBVfacet@locale@2@PEBV42@@Z
 ??1failure@ios_base@std@@UEAA@XZ
 _CT??_R0?AVruntime_error@std@@@8??0runtime_error@std@@QEAA@AEBV01@@Z24
 ?do_narrow@?$ctype@D@std@@MEBAPEBDPEBD0DPEAD@Z
 ??$_Construct@$01PEBD@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAAXQEBD_K@Z
 _CTA3?AVbad_array_new_length@std@@
 ??_R3system_error@std@@8
 ??0failure@ios_base@std@@QEAA@AEBV012@@Z
 ?do_widen@?$ctype@D@std@@MEBAPEBDPEBD0PEAD@Z
 ??$max@_K@std@@YAAEB_KAEB_K0@Z
 ?do_tolower@?$ctype@D@std@@MEBAPEBDPEADPEBD@Z
 ??_C@_00CNPNBAHC@?$AA@
 ?eof@?$_Narrow_char_traits@DH@std@@SAHXZ
 ??$_Adl_verify_range@PEADPEBD@std@@YAXAEBQEADAEBQEBD@Z
 ??_R2exception@std@@8
 ??_7failure@ios_base@std@@6B@
 ?clear@ios_base@std@@QEAAXH_N@Z
 ??_R0?AU_Crt_new_delete@std@@@8
 ??_7system_error@std@@6B@
 ??_Gexception@std@@UEAAPEAXI@Z
 ?_Getctype@_Locinfo@std@@QEBA?AU_Ctypevec@@XZ
 ?width@ios_base@std@@QEBA_JXZ
 ?good@ios_base@std@@QEBA_NXZ
 ??_R4_Facet_base@std@@6B@
 ??_C@_0BF@PHHKMMFD@ios_base?3?3badbit?5set?$AA@
 ??$endl@DU?$char_traits@D@std@@@std@@YAAEAV?$basic_ostream@DU?$char_traits@D@std@@@0@AEAV10@@Z
 ??$_Allocate_for_capacity@$0A@@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@CAPEADAEAV?$allocator@D@1@AEA_K@Z
 ??0?$allocator@D@std@@QEAA@XZ
 ??_7runtime_error@std@@6B@
 ??_R4?$ctype@D@std@@6B@
 ??$_Destroy_in_place@PEAD@std@@YAXAEAPEAD@Z
 _CT??_R0?AVbad_alloc@std@@@8??0bad_alloc@std@@QEAA@AEBV01@@Z24
 ?empty@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEBA_NXZ
 ?tie@?$basic_ios@DU?$char_traits@D@std@@@std@@QEBAPEAV?$basic_ostream@DU?$char_traits@D@std@@@2@XZ
 ?_Throw_bad_cast@std@@YAXXZ
 ??_R3_Crt_new_delete@std@@8
 ?move@?$_Char_traits@DH@std@@SAPEADQEADQEBD_K@Z
 ??_R1A@?0A@EA@_Crt_new_delete@std@@8
 ??_R3bad_alloc@std@@8
 ??_7_Facet_base@std@@6B@
 ??_R1A@?0A@EA@_Iostream_error_category2@std@@8
 ??0_System_error@std@@IEAA@Verror_code@1@AEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@1@@Z
 ?_Get_first@?$_Compressed_pair@V?$allocator@D@std@@V?$_String_val@U?$_Simple_types@D@std@@@2@$00@std@@QEAAAEAV?$allocator@D@2@XZ
 ??1facet@locale@std@@MEAA@XZ
 ??_R1A@?0A@EA@exception@std@@8
 ??_R0?AVsystem_error@std@@@8
 ??_G?$ctype@D@std@@MEAAPEAXI@Z
 ??_R0?AVbad_array_new_length@std@@@8
 ?_Decref@facet@locale@std@@UEAAPEAV_Facet_base@3@XZ
 ??_R3failure@ios_base@std@@8
 ?_Tidy@?$_Yarn@D@std@@AEAAXXZ
 ??_R1A@?0A@EA@bad_alloc@std@@8
 ??0failure@ios_base@std@@QEAA@PEBDAEBVerror_code@2@@Z
 ??1_Bxty@?$_String_val@U?$_Simple_types@D@std@@@std@@QEAA@XZ
 ?do_toupper@?$ctype@D@std@@MEBADD@Z
 ??_R4failure@ios_base@std@@6B@
 ??_R3_System_error@std@@8
 ?_Static@?1???$_Immortalize_memcpy_image@V_Iostream_error_category2@std@@@std@@YAAEBV_Iostream_error_category2@1@XZ@4V21@B
 ??$_Reallocate_grow_by@V<lambda_1>@?0??append@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAAAEAV34@QEBD_K@Z@PEBD_K@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAAAEAV01@_KV<lambda_1>@?0??append@01@QEAAAEAV01@QEBD0@Z@PEBD_K@Z
 ??$?0AEAPEAV_Facet_base@std@@@?$_Compressed_pair@U?$default_delete@V_Facet_base@std@@@std@@PEAV_Facet_base@2@$00@std@@QEAA@U_Zero_then_variadic_args_t@1@AEAPEAV_Facet_base@1@@Z
 ??_R4_System_error@std@@6B@
 ??_R0?AVexception@std@@@8
 ?copy@?$_Char_traits@DH@std@@SAPEADQEADQEBD_K@Z
 ??_G_Iostream_error_category2@std@@UEAAPEAXI@Z
 ??_R3?$ctype@D@std@@8
 ??_R0?AVfailure@ios_base@std@@@8
 ??_R3runtime_error@std@@8
 ??_R2?$ctype@D@std@@8
 ?sputn@?$basic_streambuf@DU?$char_traits@D@std@@@std@@QEAA_JPEBD_J@Z
 ?_Deallocate_for_capacity@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@CAXAEAV?$allocator@D@2@QEAD_K@Z
 ??1_Locinfo@std@@QEAA@XZ
 ??0error_condition@std@@QEAA@HAEBVerror_category@1@@Z
 ??_R2_Iostream_error_category2@std@@8
 ??_R1A@?0A@EA@failure@ios_base@std@@8
 ?_Incref@facet@locale@std@@UEAAXXZ
 ??1?$ctype@D@std@@MEAA@XZ
 ??0?$_Yarn@D@std@@QEAA@XZ
 ??1?$_Yarn@D@std@@QEAA@XZ
 ??1_Sentry_base@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAA@XZ
 ??1_Facet_base@std@@UEAA@XZ
 _TI3?AVbad_array_new_length@std@@
 ??_C@_0BA@JFNIOLAK@string?5too?5long?$AA@
 ??_R3_Facet_base@std@@8
 ??$?0V?$allocator@D@std@@$$V@?$_Compressed_pair@V?$allocator@D@std@@V?$_String_val@U?$_Simple_types@D@std@@@2@$00@std@@QEAA@U_One_then_variadic_args_t@1@$$QEAV?$allocator@D@1@@Z
 ??_G_Facet_base@std@@UEAAPEAXI@Z
 ?_Calculate_growth@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEBA_K_K@Z
 ??0_Facet_base@std@@QEAA@XZ
 ?equivalent@error_category@std@@UEBA_NHAEBVerror_condition@2@@Z
 ??_R1A@?0A@EA@ctype_base@std@@8
 ??_R2bad_array_new_length@std@@8
 ?do_narrow@?$ctype@D@std@@MEBADDD@Z
 ?pubsync@?$basic_streambuf@DU?$char_traits@D@std@@@std@@QEAAHXZ
 ??_R1A@?0A@EA@bad_array_new_length@std@@8
 ??0?$ctype@D@std@@QEAA@AEBV_Locinfo@1@_K@Z
 ??_R2_System_error@std@@8
 ??1ctype_base@std@@UEAA@XZ
 ??_R1A@?0A@EA@?$ctype@D@std@@8
 ??_R0?AV?$ctype@D@std@@@8
 ?_Init@?$ctype@D@std@@IEAAXAEBV_Locinfo@2@@Z
 ??0sentry@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAA@AEAV12@@Z
 ??1?$_Compressed_pair@V?$allocator@D@std@@V?$_String_val@U?$_Simple_types@D@std@@@2@$00@std@@QEAA@XZ
 ??_C@_04BBBJENEO@oops?$AA@
 ?_Tidy@?$_Yarn@_W@std@@AEAAXXZ
 ??_7exception@std@@6B@
 ??_C@_02LMMGGCAJ@?3?5?$AA@
 ??_R4runtime_error@std@@6B@
 ??_Gctype_base@std@@UEAAPEAXI@Z
 ??_R1A@?0A@EA@runtime_error@std@@8
 ??$_Allocate_manually_vector_aligned@U_Default_allocate_traits@std@@@std@@YAPEAX_K@Z
 ?rdbuf@?$basic_ios@DU?$char_traits@D@std@@@std@@QEBAPEAV?$basic_streambuf@DU?$char_traits@D@std@@@2@XZ
 ??_R4system_error@std@@6B@
 ?widen@?$basic_ios@DU?$char_traits@D@std@@@std@@QEBADD@Z
 ??0bad_cast@std@@QEAA@AEBV01@@Z
 ??_C@_08LLGCOLLL@iostream?$AA@
 ??_R4ctype_base@std@@6B@
 ??0ctype_base@std@@QEAA@_K@Z
 ??_R0?AVbad_alloc@std@@@8
 ??_R0?AV_Iostream_error_category2@std@@@8
 ??_R2facet@locale@std@@8
 ??1bad_cast@std@@UEAA@XZ
 ??0facet@locale@std@@IEAA@_K@Z
 ?_Fake_alloc@std@@3U_Fake_allocator@1@B
 _CTA5?AVfailure@ios_base@std@@
 ??_R2runtime_error@std@@8
 ??_R2bad_cast@std@@8
 ??_C@_0BG@FMKFHCIL@ios_base?3?3failbit?5set?$AA@
 ??_R1A@?0A@EA@_System_error@std@@8
 ?message@error_code@std@@QEBA?AV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@2@XZ
 ??1?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAA@XZ
 ??0?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAA@QEBD_K@Z
 ??_R2failure@ios_base@std@@8
 ??0?$_String_val@U?$_Simple_types@D@std@@@std@@QEAA@XZ
 ??0?$_Yarn@_W@std@@QEAA@XZ
 ?c_str@?$_Yarn@D@std@@QEBAPEBDXZ
 ?_Myptr@?$_String_val@U?$_Simple_types@D@std@@@std@@QEAAPEADXZ
 ?_Take_contents@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAAXAEAV12@@Z
 ?to_int_type@?$_Narrow_char_traits@DH@std@@SAHD@Z
 ?_Makestr@_System_error@std@@CA?AV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@2@Verror_code@2@V32@@Z
 ?do_widen@?$ctype@D@std@@MEBADD@Z
 ?_Large_mode_engaged@?$_String_val@U?$_Simple_types@D@std@@@std@@QEBA_NXZ
 ??_R4bad_cast@std@@6B@
 ??_R2error_category@std@@8
 ??0bad_cast@std@@QEAA@XZ
 ??0exception@std@@QEAA@QEBDH@Z
 __orc_init_func.incr_module_3
 ?max@?$numeric_limits@_J@std@@SA_JXZ
 ??$_Get_size_of_n@$00@std@@YA_K_K@Z
 ??_R3bad_cast@std@@8
 ?_Tidy_deallocate@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAAXXZ
 ?_C_str@locale@std@@QEBAPEBDXZ
 ?message@_Iostream_error_category2@std@@UEBA?AV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@2@H@Z
 _TI2?AVbad_cast@std@@
 ??1sentry@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAA@XZ
 ??8error_category@std@@QEBA_NAEBV01@@Z
 ??6?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAAAEAV01@P6AAEAV01@AEAV01@@Z@Z
 ??_7bad_alloc@std@@6B@
 ??Bsentry@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEBA_NXZ
 ??_Gsystem_error@std@@UEAAPEAXI@Z
 ?c_str@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEBAPEBDXZ
 ??0bad_array_new_length@std@@QEAA@XZ
 ?setstate@?$basic_ios@DU?$char_traits@D@std@@@std@@QEAAXH_N@Z
 ??_R2_Facet_base@std@@8
 ??_C@_08EPJLHIJG@bad?5cast?$AA@
 ??0?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAA@QEBD@Z
 ??_Gruntime_error@std@@UEAAPEAXI@Z
 ??_R1A@?0A@EA@bad_cast@std@@8
 ?width@ios_base@std@@QEAA_J_J@Z
 ?_Calculate_growth@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@CA_K_K00@Z
 ??_R4exception@std@@6B@
 ??1?$unique_ptr@V_Facet_base@std@@U?$default_delete@V_Facet_base@std@@@2@@std@@QEAA@XZ
 ?_Xlen_string@std@@YAXXZ
 ??1error_category@std@@UEAA@XZ
 $.incr_module_3.__inits.0
 ??0_Sentry_base@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAA@AEAV12@@Z
 ??0runtime_error@std@@QEAA@AEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@1@@Z
 ??R<lambda_1>@?0??append@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAAAEAV23@QEBD_K@Z@SA?A?<auto>@@QEAD0101@Z
 ?length@?$_Narrow_char_traits@DH@std@@SA_KQEBD@Z
 ??_R2ctype_base@std@@8
 ??1?$_Yarn@_W@std@@QEAA@XZ
 ??$_Construct_in_place@PEADAEBQEAD@std@@YAXAEAPEADAEBQEAD@Z
 ??_R0?AV_System_error@std@@@8
 ??_R3bad_array_new_length@std@@8
 ??_R3_Iostream_error_category2@std@@8
 ??_R0?AVerror_category@std@@@8
 ??_7?$ctype@D@std@@6B@
 ??$exchange@PEAV_Facet_base@std@@$$T@std@@YAPEAV_Facet_base@0@AEAPEAV10@$$QEA$$T@Z
 ?_Get_first@?$_Compressed_pair@V?$allocator@D@std@@V?$_String_val@U?$_Simple_types@D@std@@@2@$00@std@@QEBAAEBV?$allocator@D@2@XZ
 ??_R0?AUctype_base@std@@@8
 _CTA2?AVbad_cast@std@@
 ??_R4bad_array_new_length@std@@6B@
 ??0?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAA@AEBV01@@Z
 ??_R1A@?0A@EA@system_error@std@@8
 ??0_Bxty@?$_String_val@U?$_Simple_types@D@std@@@std@@QEAA@XZ
 ?_Getfacet@locale@std@@QEBAPEBVfacet@12@_K@Z
 ??_Gfacet@locale@std@@MEAAPEAXI@Z
 ??$?0U?$default_delete@V_Facet_base@std@@@std@@$0A@@?$unique_ptr@V_Facet_base@std@@U?$default_delete@V_Facet_base@std@@@2@@std@@QEAA@PEAV_Facet_base@1@@Z
 ?_Tidy@?$ctype@D@std@@IEAAXXZ
 ?append@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QEAAAEAV12@QEBD@Z
 ?do_tolower@?$ctype@D@std@@MEBADD@Z
 ?do_toupper@?$ctype@D@std@@MEBAPEBDPEADPEBD@Z
 ??_C@_0BC@EOODALEL@Unknown?5exception?$AA@
 ??_R3error_category@std@@8
 ??_Gbad_alloc@std@@UEAAPEAXI@Z
 ?flush@?$basic_ostream@DU?$char_traits@D@std@@@std@@QEAAAEAV12@XZ
 ??_R1A@?0A@EA@_Facet_base@std@@8
 ??_R3ctype_base@std@@8
 _TI5?AVfailure@ios_base@std@@
 ??_R0?AV_Facet_base@std@@@8
 ?_Pninc@?$basic_streambuf@DU?$char_traits@D@std@@@std@@IEAAPEADXZ
 ??_7ctype_base@std@@6B@
 ??_R1A@?0A@EA@facet@locale@std@@8
 ??$?0$$V@?$_Compressed_pair@V?$allocator@D@std@@V?$_String_val@U?$_Simple_types@D@std@@@2@$00@std@@QEAA@U_Zero_then_variadic_args_t@1@@Z
 ??0_Locinfo@std@@QEAA@PEBD@Z
 ??_R0?AVfacet@locale@std@@@8
 ??0locale@std@@QEAA@AEBV01@@Z
 ??_R4_Iostream_error_category2@std@@6B@
 ??_R0?AVbad_cast@std@@@8
 ?clear@?$basic_ios@DU?$char_traits@D@std@@@std@@QEAAXH_N@Z
 ??_R3facet@locale@std@@8
 ??$_Construct@$00PEBD@?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAAXQEBD_K@Z
 ??_Gbad_cast@std@@UEAAPEAXI@Z
 )
    if($<CONFIG:Debug>)
        set(xeus_cpp_exports ${xeus_cpp_exports} ??$dyn_cast@VValueDecl@clang@@$$CBVDecl@2@@llvm@@YAPEBVValueDecl@clang@@PEBVDecl@2@@Z)
    endif()

    # List to '/EXPORT:sym0 /EXPORT:sym1 /EXPORT:sym2 ...'
    foreach(sym ${xeus_cpp_exports})
        set(xeus_cpp _link_str "${xeus_cpp_link_str} /EXPORT:${sym}")
    endforeach(sym ${xeus_cpp_exports})

    set_property(TARGET xeus-cpp APPEND_STRING PROPERTY LINK_FLAGS ${xeus_cpp_link_str})
endif(MSVC)


# Tests
# =====

if(XEUS_CPP_BUILD_TESTS)
    add_subdirectory(test)
endif()

# Installation
# ============
include(CMakePackageConfigHelpers)

set(XEUS_CPP_CMAKECONFIG_INSTALL_DIR "${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECT_NAME}" CACHE STRING "install path for xeus-cppConfig.cmake")

install(DIRECTORY ${XCPP_TAGFILES_DIR}
        DESTINATION ${XEUS_CPP_DATA_DIR})

install(DIRECTORY ${XCPP_TAGCONFS_DIR}
        DESTINATION ${XEUS_CPP_CONF_DIR})

# Install xeus-cpp and xeus-cpp-static
if (XEUS_CPP_BUILD_SHARED)
    install(TARGETS ${XEUS_CPP_TARGETS}
            EXPORT ${PROJECT_NAME}-targets
            ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
            LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
            RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
            PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/xeus-cpp)

    # Makes the project importable from the build directory
    export(EXPORT ${PROJECT_NAME}-targets
           FILE "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}Targets.cmake")
endif ()

# Install xcpp
if (XEUS_CPP_BUILD_EXECUTABLE)
    install(TARGETS xcpp
            RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()

if(XEUS_CPP_BUILD_EXECUTABLE OR EMSCRIPTEN)
    # Configuration and data directories for jupyter and xeus-cpp
    set(XJUPYTER_DATA_DIR "share/jupyter"    CACHE STRING "Jupyter data directory")

    # Install xcpp Jupyter kernelspec
    set(KERNELSPEC_DIR ${CMAKE_CURRENT_BINARY_DIR}/share/jupyter/kernels)
    install(DIRECTORY ${KERNELSPEC_DIR}
            DESTINATION ${XJUPYTER_DATA_DIR}
            PATTERN "*.in" EXCLUDE)


    # Extra path for installing Jupyter kernelspec
    if (XEXTRA_JUPYTER_DATA_DIR)
        install(DIRECTORY ${KERNELSPEC_DIR}
                DESTINATION ${XEXTRA_JUPYTER_DATA_DIR}
                PATTERN "*.in" EXCLUDE)
    endif ()
endif ()

# Configure 'xeus-cppConfig.cmake' for a build tree
set(XEUS_CPP_CONFIG_CODE "####### Expanded from \@XEUS_CPP_CONFIG_CODE\@ #######\n")
set(XEUS_CPP_CONFIG_CODE "${XEUS_CPP_CONFIG_CODE}set(CMAKE_MODULE_PATH \"${CMAKE_CURRENT_SOURCE_DIR}/cmake;\${CMAKE_MODULE_PATH}\")\n")
set(XEUS_CPP_CONFIG_CODE "${XEUS_CPP_CONFIG_CODE}##################################################")
configure_package_config_file(${PROJECT_NAME}Config.cmake.in
                              "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}Config.cmake"
                              INSTALL_DESTINATION ${PROJECT_BINARY_DIR})

# Configure 'xeus-cppConfig.cmake.in for an install tree
set(XEUS_CPP_CONFIG_CODE "")
configure_package_config_file(${PROJECT_NAME}Config.cmake.in
                              "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/${PROJECT_NAME}Config.cmake"
                              INSTALL_DESTINATION ${XEUS_CPP_CMAKECONFIG_INSTALL_DIR})

write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}ConfigVersion.cmake
                                 VERSION ${${PROJECT_NAME}_VERSION}
                                 COMPATIBILITY AnyNewerVersion)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/${PROJECT_NAME}Config.cmake
              ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}ConfigVersion.cmake
              DESTINATION ${XEUS_CPP_CMAKECONFIG_INSTALL_DIR})

if (XEUS_CPP_BUILD_SHARED)
    install(EXPORT ${PROJECT_NAME}-targets
            FILE ${PROJECT_NAME}Targets.cmake
            DESTINATION ${XEUS_CPP_CMAKECONFIG_INSTALL_DIR})
endif ()

if(EMSCRIPTEN)
    install(TARGETS xcpp
            ARCHIVE DESTINATION ${XEUS_CPP_CMAKECONFIG_INSTALL_DIR})

    install(FILES
            "$<TARGET_FILE_DIR:xcpp>/xcpp.js"
            "$<TARGET_FILE_DIR:xcpp>/xcpp.wasm"
            DESTINATION ${CMAKE_INSTALL_BINDIR})
endif ()

if(XEUS_CPP_INCLUDE_DOCS)
    add_subdirectory(docs)
endif()
