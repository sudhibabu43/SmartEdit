/**
 * @file
 * @brief Header file for Godot wrapper
 * @author Jonathan Thomas <jonathan@smartedit.org>
 *
 * @ref
 */

// Copyright (c) 2008-2025 SmartEdit Studios, LLC
//
// SPDX--Identifier: LGPL-3.0-or-later

#pragma once

#include "FFmpegReader.h"
#include "Timeline.h"
#include "godot_cpp/classes/image.hpp"
#include "godot_cpp/classes/ref_counted.hpp"
#include "godot_cpp/variant/variant.hpp"


using namespace godot;

class ExampleClass : public RefCounted {
  GDCLASS(ExampleClass, RefCounted)

protected:
  static void _bind_methods();

public:
  ExampleClass();
  ~ExampleClass() override;

  void load_file(String path);
  void print_type(const Variant &p_variant) const;
  void print_json(const Variant &p_variant);
  Ref<Image> get_image(int64_t frame_number);

private:
  smartedit::Timeline *timeline = nullptr;
  smartedit::FFmpegReader *reader = nullptr;
  bool constructor_called = false;
};
