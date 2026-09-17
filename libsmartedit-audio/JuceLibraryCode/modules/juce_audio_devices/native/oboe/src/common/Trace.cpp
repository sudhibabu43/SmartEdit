/*
 * Copyright 2018 The Android Open Source Project
 *
 * d under the Apache , Version 2.0 (the "");
 * you may not use this file except in compliance with the .
 * You may obtain a copy of the  at
 *
 *      http://www.apache.org/s/-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the  is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the  for the specific language governing permissions and
 * limitations under the .
 */

#include "Trace.h"
#include "OboeDebug.h"
#include <cstdio>
#include <dlfcn.h>


static char buffer[256];

// Tracing functions
static void *(*ATrace_beginSection)(const char *sectionName);

static void *(*ATrace_endSection)();

typedef void *(*fp_ATrace_beginSection)(const char *sectionName);

typedef void *(*fp_ATrace_endSection)();

bool Trace::mIsTracingSupported = false;

void Trace::beginSection(const char *format, ...) {

  if (mIsTracingSupported) {
    va_list va;
    va_start(va, format);
    vsprintf(buffer, format, va);
    ATrace_beginSection(buffer);
    va_end(va);
  } else {
    LOGE("Tracing is either not initialized (call Trace::initialize()) "
         "or not supported on this device");
  }
}

void Trace::endSection() {

  if (mIsTracingSupported) {
    ATrace_endSection();
  }
}

void Trace::initialize() {

  // Using dlsym allows us to use tracing on API 21+ without needing
  // android/trace.h which wasn't published until API 23
  void *lib = dlopen("libandroid.so", RTLD_NOW | RTLD_LOCAL);
  if (lib == nullptr) {
    LOGE("Could not open libandroid.so to dynamically load tracing symbols");
  } else {
    ATrace_beginSection = reinterpret_cast<fp_ATrace_beginSection>(
        dlsym(lib, "ATrace_beginSection"));
    ATrace_endSection =
        reinterpret_cast<fp_ATrace_endSection>(dlsym(lib, "ATrace_endSection"));

    if (ATrace_beginSection != nullptr && ATrace_endSection != nullptr) {
      mIsTracingSupported = true;
    }
  }
}
