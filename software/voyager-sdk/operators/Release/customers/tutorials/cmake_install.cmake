# Install script for directory: /home/orangepi/abc/software/voyager-sdk/customers/tutorials

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/orangepi/abc/software/voyager-sdk/operators")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/libdecode_tu6a.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6a.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/CMakeFiles/decode_tu6a.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/libdecode_tu6b.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu6b.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/CMakeFiles/decode_tu6b.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/libdecode_tu7.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu7.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/CMakeFiles/decode_tu7.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/libdecode_tu9.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_tu9.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/CMakeFiles/decode_tu9.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/libinplace_tu9.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tu9.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/CMakeFiles/inplace_tu9.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
