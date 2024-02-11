#include <pybind11/pybind11.h>
namespace py = pybind11;
using namespace pybind11::literals;

#include <stdexcept>
#include <string>

#define TSF_IMPLEMENTATION
#include "tsf/tsf.h"

class SoundFont {
private:
    tsf* obj = nullptr;
public:
    SoundFont(const std::string& filename)
    {
        obj = tsf_load_filename(filename.c_str());
        if (!obj) {
            throw std::runtime_error("Could not load SoundFont file: " + filename);
        }
    }
    ~SoundFont() {
        tsf_close(obj);
    }
    void reset() { tsf_reset(obj); }
    int get_preset_index(int bank, int number) { return tsf_get_presetindex(obj, bank, number); }
    int get_preset_count() { return tsf_get_presetcount(obj); }
    std::string get_preset_name(int index) { return std::string(tsf_get_presetname(obj, index)); }
    std::string get_preset_name(int bank, int number) { return tsf_bank_get_presetname(obj, bank, number); }
};

PYBIND11_MODULE(tinysoundfont, m) {
    m.doc() = "Tiny Sound Font module";
    py::enum_<enum TSFOutputMode>(m, "OutputMode")
        .value("StereoInterleaved", TSF_STEREO_INTERLEAVED)
        .value("StereoUnweaved", TSF_STEREO_UNWEAVED)
        .value("Mono", TSF_MONO)
    ;
    py::class_<SoundFont>(m, "SoundFont")
        .def(py::init<const std::string &>(),
            "Directly load a SoundFont from a .sf2 filename",
            "filename"_a)
        .def("reset", &SoundFont::reset,
            "Stop all playing notes immediately and reset all channel parameters")
        .def("get_preset_index", &SoundFont::get_preset_index,
            "Returns the preset index from a bank and preset number, or -1 if it does not exist in the loaded SoundFont",
            "bank"_a, "preset"_a)
        .def("get_preset_count", &SoundFont::get_preset_count,
            "Returns the number of presets in the loaded SoundFont")
        .def("get_preset_name", py::overload_cast<int>(&SoundFont::get_preset_name),
            "Returns the name of a preset index >= 0 and < get_preset_count()",
            "index"_a)
        .def("get_preset_name", py::overload_cast<int, int>(&SoundFont::get_preset_name),
            "Returns the name of a preset by bank and preset number",
            "bank"_a, "number"_a)
    ;
}
