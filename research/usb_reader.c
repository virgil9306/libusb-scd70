#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <libusb-1.0/libusb.h>

static PyObject* usb_read_fast(PyObject* self, PyObject* args) {
    unsigned long dev_handle_ptr;
    int endpoint;
    int length;
    int timeout;
    
    if (!PyArg_ParseTuple(args, "kiii", &dev_handle_ptr, &endpoint, &length, &timeout)) {
        return NULL;
    }
    
    libusb_device_handle* handle = (libusb_device_handle*)dev_handle_ptr;
    
    unsigned char* buffer = (unsigned char*)malloc(length);
    if (!buffer) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate buffer");
        return NULL;
    }
    
    int transferred;
    int result = libusb_bulk_transfer(handle, endpoint, buffer, length, &transferred, timeout);
    
    if (result < 0 && result != LIBUSB_ERROR_TIMEOUT) {
        free(buffer);
        PyErr_Format(PyExc_IOError, "USB read error: %s", libusb_error_name(result));
        return NULL;
    }
    
    PyObject* bytes_obj = PyBytes_FromStringAndSize((char*)buffer, transferred);
    free(buffer);
    
    return bytes_obj;
}

static PyMethodDef UsbReaderMethods[] = {
    {"read_fast", usb_read_fast, METH_VARARGS, "Fast USB bulk read"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef usbreadermodule = {
    PyModuleDef_HEAD_INIT,
    "usb_reader",
    "Fast USB reading module",
    -1,
    UsbReaderMethods
};

PyMODINIT_FUNC PyInit_usb_reader(void) {
    return PyModule_Create(&usbreadermodule);
}
