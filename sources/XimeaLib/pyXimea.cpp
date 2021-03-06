#include "ximea.h"
#include "export.h"
#include <numpy/ndarrayobject.h>
#include <datetime.h>
#include "structmember.h"

#ifdef __cplusplus
extern "C" {
#endif

CaptureCAM_XIMEA* capt;
PyObject *myDict = PyDict_New();
PyObject *rslt = PyTuple_New(2);
PyObject *rslt_data = PyTuple_New(2);
char *array_buffer;

PyObject*
VideoCapture_open(int device)
{
    if (VideoCapture_isOpened() == Py_True) {
		VideoCapture_release();
	}
	capt->open(device);
    return VideoCapture_isOpened();
}

PyObject*
VideoCapture_openByName(char * device_path)
{
    if (VideoCapture_isOpened() == Py_True) {
		VideoCapture_release();
	}
	capt->open(device_path);
    return VideoCapture_isOpened();
}

PyObject*
VideoCapture_addTrigger(VideoCapture *self, PyObject *args)
{
    int timeout;
    bool triggered;
    if (!PyArg_ParseTuple(args, "ib", &timeout, &triggered)){
    	cout << "arg must be (int, bool). " << endl;
        Py_INCREF(Py_None);
        return Py_None;
    }
    capt->addTrigger(timeout, triggered);
    return Py_None;
}



PyObject*
VideoCapture_isOpened()
{
    PyObject* ret = Py_False;
    if(capt->isopened) {
        ret=Py_True;
        Py_INCREF(ret);
        return ret;
    }else{
        Py_INCREF(ret);
        return ret;
    }
}

PyObject*
VideoCapture_release()
{
    capt->close();
    PyObject* ret = Py_None;
    Py_INCREF(ret);
    return ret;
}

bool VideoCapture_grab()
{
    return capt->grabFrame();
}


PyObject* VideoCapture_retrieve(VideoCapture *self)
{
		switch(capt->image.frm)
		{
		case XI_MONO8: {
            const int ndim = 2;
            npy_intp nd[2] = {capt->height, capt->width};
            Py_XDECREF(self->myarray);
            self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT8, capt->image.bp);
            Py_XDECREF(nd);
            break;
		}
		case XI_MONO16:{ 
			const int ndim = 2;
			npy_intp nd[2] = {capt->height, capt->width};
			Py_XDECREF(self->myarray);
			self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT16, capt->image.bp);
			Py_XDECREF(nd);
			break;
		}
		case XI_RGB24       : {
			const int ndim = 3;
			npy_intp nd[3] = {capt->height, capt->width, 3};
			Py_XDECREF(self->myarray);
			self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT8, capt->image.bp);
			Py_XDECREF(nd);
			break;}
		case XI_RGB32       : {
			const int ndim = 4;
			npy_intp nd[3] = {capt->height, capt->width, 4};
			Py_XDECREF(self->myarray);
			self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT8, capt->image.bp);
			Py_XDECREF(nd);
			break;}
		case XI_RGB_PLANAR  : {
			const int ndim = 3;
			npy_intp nd[3] = {capt->height, capt->width, 3};
			Py_XDECREF(self->myarray);
			self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT8, capt->image.bp);
			Py_XDECREF(nd);
			break;}
		case XI_RAW8        : {
			const int ndim = 2;
			npy_intp nd[2] = {capt->height, capt->width};
			Py_XDECREF(self->myarray);
			self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT8, capt->image.bp);
			Py_XDECREF(nd);
			break;}
		case XI_RAW16       : {
			const int ndim = 3;
			npy_intp nd[3] = {capt->height, capt->width, 2};
			Py_XDECREF(self->myarray);
			self->myarray = PyArray_SimpleNewFromData(ndim, nd, NPY_UINT16, capt->image.bp);
			Py_XDECREF(nd);
			break;}
		default : 
			return Py_None;
		}
		capt-> resetCvImage();
		myDict = PyDict_New();
		myDict = VideoCapture_getMeta();
		PyDict_SetItemString(myDict, "data", self->myarray);
    return myDict;
}

PyObject*
VideoCapture_getMeta()
{
	PyDateTime_IMPORT;
	PyDict_SetItemString(myDict, "width", Py_BuildValue("I", capt->image.width));
	PyDict_SetItemString(myDict, "height", Py_BuildValue("I",capt->image.height));
// 	PyDict_SetItemString(myDict, "bp_size", Py_BuildValue("I",capt->image.bp_size));
// 	PyDict_SetItemString(myDict, "size", Py_BuildValue("I",capt->image.size));
// 	PyDict_SetItemString(myDict, "GPI_level", Py_BuildValue("I",capt->image.GPI_level));
// 	PyDict_SetItemString(myDict, "black_level", Py_BuildValue("I",capt->image.black_level));
// 	PyDict_SetItemString(myDict, "padding_x", Py_BuildValue("I",capt->image.padding_x));
	PyDict_SetItemString(myDict, "nframe", Py_BuildValue("I",capt->image.nframe));
	PyDict_SetItemString(myDict, "AbsoluteOffsetX", Py_BuildValue("I",capt->image.AbsoluteOffsetX));
	PyDict_SetItemString(myDict, "AbsoluteOffsetY", Py_BuildValue("I",capt->image.AbsoluteOffsetY));

	PyObject *floatObj = PyFloat_FromDouble(capt->image.tsSec);
	PyObject *timeTuple = Py_BuildValue("(O)", floatObj);
	PyObject *dateTime = PyDateTime_FromTimestamp(timeTuple);
	PyDict_SetItemString(myDict, "tsSec", dateTime);
        Py_CLEAR(floatObj);
        Py_CLEAR(timeTuple);
        Py_CLEAR(dateTime);

	PyObject *floatObj1 = PyFloat_FromDouble(capt->image.tsUSec);
	PyObject *timeTuple1 = Py_BuildValue("(O)", floatObj1);
	PyObject *dateTime1 = PyDateTime_FromTimestamp(timeTuple1);
	PyDict_SetItemString(myDict, "tsUSec", dateTime1);
	Py_CLEAR(floatObj1);
        Py_CLEAR(timeTuple1);
        Py_CLEAR(dateTime1);

	return myDict;
}

PyObject*
VideoCapture_xiread(VideoCapture *self)
{
    rslt = PyTuple_New(2);
    PyObject* ret = Py_False;
    if(!VideoCapture_grab()){
                Py_INCREF(ret);
                PyTuple_SetItem(rslt, 0, ret);
                PyTuple_SetItem(rslt, 1, Py_None);
    }else{
                ret = Py_True;
                Py_INCREF(ret);
                PyTuple_SetItem(rslt, 0, ret);
                PyTuple_SetItem(rslt, 1, VideoCapture_retrieve(self));
    }
    rslt_data = PyTuple_New(2);
    rslt_data = rslt;
    return rslt_data;
}

PyObject*
VideoCapture_set(VideoCapture *self, PyObject *args)
{
	int propId;
	double value;
        PyObject* ret = Py_False;
	if (!PyArg_ParseTuple(args, "id", &propId, &value))
		exit(0);
    if(capt->setProperty(propId, value)) {
        ret = Py_True;
        Py_INCREF(ret);
        return ret;
    }else{
        ret = Py_False;
        Py_INCREF(ret);
        return ret;
    }
}

PyObject*
VideoCapture_get(VideoCapture *self, PyObject *args)
{
	int propId;
	if (!PyArg_ParseTuple(args, "i", &propId))
		exit(0);
    return Py_BuildValue("d", capt->getProperty(propId));
}

static void
VideoCapture_dealloc(VideoCapture* self)
{
    Py_XDECREF(self->myarray);
    VideoCapture_release();
    //self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
VideoCapture_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    VideoCapture *self;
    self = (VideoCapture *)type->tp_alloc(type, 0);
    self->first_read = true;
    static char *kwlist[] = {"device", "device_path", NULL};
    if (self != NULL) {
        if (! PyArg_ParseTupleAndKeywords(args, kwds, "|is", kwlist, &self->device, &self->device_path)){
                return NULL;
        }
    }

    return (PyObject *)self;
}

static int
VideoCapture_init(VideoCapture *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"device", "device_path", NULL};

    self->device = -1;
    self->device_path = "";
    if (! PyArg_ParseTupleAndKeywords(args, kwds, "|is", kwlist, &self->device, &self->device_path)){
            return NULL;
    }
    capt = new CaptureCAM_XIMEA();

    if(self->device != -1){
        VideoCapture_open(self->device);
    }else{
        VideoCapture_openByName(self->device_path);
    }
    return 0;
}


static PyMemberDef VideoCapture_members[] = {
    {NULL}
};


static PyMethodDef VideoCapture_methods[] = {
        {"read", (PyCFunction)VideoCapture_xiread, METH_NOARGS,
	 "read a frame from ximea device, return a tuple containing a bool (true= success, false= fail) and a dictionnary with a ndarray and meta."},
	 {"set", (PyCFunction)VideoCapture_set, METH_VARARGS,
	 "set the configuration parameter specified of a ximea device"},
	 {"get", (PyCFunction)VideoCapture_get, METH_VARARGS,
	 "get the configuration parameter specified of a ximea device"},
	 {"isOpened", (PyCFunction)VideoCapture_isOpened, METH_NOARGS,
	 "return true if the ximea device is opened, false otherwise."},
	 {"release", (PyCFunction)VideoCapture_release, METH_NOARGS,
	 "release the ximea device."},
         {"addTrigger", (PyCFunction)VideoCapture_addTrigger, METH_VARARGS,
	 "add an external trigger to the camera, a frame will be taken on each rising edge of the trigger."},
    {NULL}
};

static PyTypeObject VideoCaptureType = {
    PyVarObject_HEAD_INIT(NULL,0)
    "VideoCapture.VideoCapture",             /*tp_name*/
    sizeof(VideoCapture),             /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)VideoCapture_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "VideoCapture objects",           /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    VideoCapture_methods,             /* tp_methods */
    VideoCapture_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)VideoCapture_init,      /* tp_init */
    0,                         /* tp_alloc */
    VideoCapture_new,                 /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}
};

// only for windows
void set_map_to_export(){
	my_map.insert(make_pair("CAP_PROP_XI_DOWNSAMPLING", 400));// Change image resolution by binning or skipping.
	my_map.insert(make_pair("CAP_PROP_XI_DATA_FORMAT",  401));// Output data format.
	my_map.insert(make_pair("CAP_PROP_XI_OFFSET_X", 402));// Horizontal offset from the origin to the area of interest (in pixels).
	my_map.insert(make_pair("CAP_PROP_XI_OFFSET_Y" , 403));// Vertical offset from the origin to the area of interest (in pixels).
	my_map.insert(make_pair("CAP_PROP_XI_TRG_SOURCE", 404));// Defines source of trigger.
	my_map.insert(make_pair("CAP_PROP_XI_TRG_SOFTWARE", 405));// Generates an internal trigger. PRM_TRG_SOURCE must be set to TRG_SOFTWARE.
	my_map.insert(make_pair("CAP_PROP_XI_GPI_SELECTOR", 406));// Selects general purpose input
	my_map.insert(make_pair("CAP_PROP_XI_GPI_MODE", 407));// Set general purpose input mode
	my_map.insert(make_pair("CAP_PROP_XI_GPI_LEVEL", 408));// Get general purpose level
	my_map.insert(make_pair("CAP_PROP_XI_GPO_SELECTOR", 409));// Selects general purpose output
	my_map.insert(make_pair("CAP_PROP_XI_GPO_MODE", 410));// Set general purpose output mode
	my_map.insert(make_pair("CAP_PROP_XI_LED_SELECTOR", 411));// Selects camera signalling LED
	my_map.insert(make_pair("CAP_PROP_XI_LED_MODE", 412));// Define camera signalling LED functionality
	my_map.insert(make_pair("CAP_PROP_XI_MANUAL_WB", 413));// Calculates White Balance(must be called during acquisition)
	my_map.insert(make_pair("CAP_PROP_XI_AUTO_WB", 414));// Automatic white balance
	my_map.insert(make_pair("CAP_PROP_XI_AEAG", 415));// Automatic exposure/gain
	my_map.insert(make_pair("CAP_PROP_XI_EXP_PRIORITY", 416));// Exposure priority (0.5 - exposure 50%, gain 50%).
	my_map.insert(make_pair("CAP_PROP_XI_AE_MAX_LIMIT", 417));// Maximum limit of exposure in AEAG procedure
	my_map.insert(make_pair("CAP_PROP_XI_AG_MAX_LIMIT", 418));// Maximum limit of gain in AEAG procedure
	my_map.insert(make_pair("CAP_PROP_XI_AEAG_LEVEL", 419));// Average intensity of output signal AEAG should achieve(in %)
	my_map.insert(make_pair("CAP_PROP_XI_TIMEOUT", 420));// Image capture timeout in milliseconds
	my_map.insert(make_pair("CAP_PROP_XI_TIMESTAMP", 421));   // Time the image has been taken in second accurate at microsecond
	my_map.insert(make_pair("CAP_PROP_XI_FRAME_NUMBER", 422));// Frame number (reset by exposure, gain, downsampling change, auto exposure (AEAG))
	my_map.insert(make_pair("CAP_PROP_XI_OUTPUT_DATA_BIT_DEPTH", 423));// Number of byte of the camera (mandatory for data packing)
	my_map.insert(make_pair("CAP_PROP_XI_DATA_PACKING", 424));// Data packing allow to transfert efficiently image with depth over 8 bits
	my_map.insert(make_pair("CAP_PROP_GAIN",14));
	my_map.insert(make_pair("CAP_PROP_EXPOSURE",15));
	my_map.insert(make_pair("CAP_PROP_POS_FRAMES",1));
	my_map.insert(make_pair("CAP_PROP_FRAME_WIDTH",3));
	my_map.insert(make_pair("CAP_PROP_FRAME_HEIGHT",4));
	my_map.insert(make_pair("CAP_PROP_FPS",5));
}


static struct PyModuleDef moddef = {
  PyModuleDef_HEAD_INIT,
  "ximeaModule",
  "Module that allows the use of Ximea camera",
  -1,
  module_methods,
  NULL,
  NULL,
  NULL,
  NULL,
};



PyMODINIT_FUNC PyInit_ximeaModule(void)
{
	try{
    PyObject* m;
	PyObject *tmp, *d;
	import_array();
    if (PyType_Ready(&VideoCaptureType) < 0)
		cout << "unable to install ximea module" << endl;

    m = PyModule_Create(&moddef);

    if (m == NULL)
		cout << ( "unable to install ximea module" ) << endl;

	#if defined WIN32 || defined _WIN32
	set_map_to_export();
	#endif
	d = PyModule_GetDict(m);
	map<string, int>::iterator p;
	for(p = my_map.begin(); p != my_map.end(); p++)
	{
		tmp = Py_BuildValue("i", p->second);
		PyDict_SetItemString(d, (char *)p->first.c_str(), tmp);
		Py_DECREF(tmp);
	}

    Py_INCREF(&VideoCaptureType);
    PyModule_AddObject(m, "VideoCapture", (PyObject *)&VideoCaptureType);
    return m;
    }
    catch ( const std::exception & e )
    {
        std::cerr << e.what();
    }
}
#ifdef __cplusplus
}
#endif
