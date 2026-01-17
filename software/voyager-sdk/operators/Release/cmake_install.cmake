# Install script for directory: /home/orangepi/abc/software/voyager-sdk/operators

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
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so"
         RPATH "")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer/libaxstreamer.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so"
         OLD_RPATH "/opt/axelera/runtime-1.5.2-1/lib:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaxstreamer.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/pkgconfig/axstreamer.pc")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib/pkgconfig" TYPE FILE MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so"
         RPATH "")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/gstaxstreamer/libgstaxstreamer.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so"
         OLD_RPATH "/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libgstaxstreamer.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtrackerfilter_numsubtaskruns.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerfilter_numsubtaskruns.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/trackerfilter_numsubtaskruns.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtrackerattribute_bestscore.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_bestscore.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/trackerattribute_bestscore.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtrackerattribute_mostfrequent.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtrackerattribute_mostfrequent.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/trackerattribute_mostfrequent.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_classification.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_classification.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_classification.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_faceboxes.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faceboxes.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_faceboxes.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_facerec.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facerec.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_facerec.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_faciallandmarks.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_faciallandmarks.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_faciallandmarks.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_image.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_image.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_image.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_ctc.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ctc.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_ctc.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_retinaface.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_retinaface.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_retinaface.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_rtmdet.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_rtmdet.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_rtmdet.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_semantic_seg.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_semantic_seg.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_semantic_seg.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_ssd2.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_ssd2.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_ssd2.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_to_raw_tensor.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_to_raw_tensor.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_to_raw_tensor.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolo.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolo.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolo.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolov5.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov5.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolov5.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolov8.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolov8.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolov_obb.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov_obb.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolov_obb.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolov10_simple.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov10_simple.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolov10_simple.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolov8seg.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolov8seg.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolov8seg.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_yolox.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_yolox.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_yolox.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_addstreamid.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addstreamid.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_addstreamid.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_addtiles.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_addtiles.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_addtiles.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_draw.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_draw.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_draw.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_filterdetections.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_filterdetections.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_filterdetections.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_hidemeta.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_hidemeta.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_hidemeta.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_nms.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_nms.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_nms.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_centrecropextra.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_centrecropextra.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_centrecropextra.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_colorconvert.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_colorconvert.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_contrastnormalize.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_contrastnormalize.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_contrastnormalize.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_cropresize.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_cropresize.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_cropresize.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_dequantize.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_dequantize.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_dequantize.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_facealign.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_facealign.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_facealign.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_padding.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_padding.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_padding.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_paddingdequantize.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_paddingdequantize.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_paddingdequantize.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_resize.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_resize.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_roicrop.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_roicrop.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_roicrop.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_totensor.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_totensor.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_totensor.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_postamble.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_postamble.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_postamble.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_yolopreproc.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_yolopreproc.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_yolopreproc.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_multihead.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_multihead.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_multihead.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_embeddings.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_embeddings.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_embeddings.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libdecode_facenet.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libdecode_facenet.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/decode_facenet.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_polar.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_polar.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_barrelcorrect_cl.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_barrelcorrect_cl.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_barrelcorrect_cl.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_colorconvert_cl.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_colorconvert_cl.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_colorconvert_cl.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_normalize_cl.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_normalize_cl.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_normalize_cl.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_perspective_cl.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_perspective_cl.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_perspective_cl.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_resize_cl.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resize_cl.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_resize_cl.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_polar_cl.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_polar_cl.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_polar_cl.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_normalize.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_normalize.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_normalize.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libtransform_resizeratiocropexcess.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libtransform_resizeratiocropexcess.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/transform_resizeratiocropexcess.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so"
         RPATH "")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/orangepi/abc/software/voyager-sdk/operators/lib" TYPE SHARED_LIBRARY MESSAGE_LAZY FILES "/home/orangepi/abc/software/voyager-sdk/operators/Release/libinplace_tracker.so")
  if(EXISTS "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so"
         OLD_RPATH "/home/orangepi/abc/software/voyager-sdk/operators/onnxruntime/onnxruntime/lib:/opt/axelera/runtime-1.5.2-1/lib:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers:/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/axtracker:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/bytetrack:/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/algorithms/oc_sort:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/orangepi/abc/software/voyager-sdk/operators/lib/libinplace_tracker.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/CMakeFiles/inplace_tracker.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/PillowResize/cmake_install.cmake")
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/trackers/cmake_install.cmake")
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/axstreamer/cmake_install.cmake")
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/gstaxstreamer/cmake_install.cmake")
  include("/home/orangepi/abc/software/voyager-sdk/operators/Release/customers/tutorials/cmake_install.cmake")

endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/orangepi/abc/software/voyager-sdk/operators/Release/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/orangepi/abc/software/voyager-sdk/operators/Release/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
