
print """
XXX fixme: in pyPetriDishCtrl.py,
pyPetriDishCtrl.setAvidaSlot(),
most of the code in this function should only be performed when
self.m_avida is not None.
@kgn
"""

from AvidaCore import cConfig

from math import exp
from qt import PYSIGNAL, QBrush, QColor, QLayout, QPen, QSize, Qt, QVBoxLayout, QWidget, QWMatrix
from qtcanvas import QCanvas, QCanvasRectangle
from pyPetriCanvasView import pyPetriCanvasView
from pyPopulationCellItem import pyPopulationCellItem
#from pyPetriDishView import pyPetriDishView

#class pyPetriDishCtrl(pyPetriDishView):
class pyPetriDishCtrl(QWidget):
  def __init__(self,parent = None,name = None,fl = 0):
    #pyPetriDishView.__init__(self,parent,name,fl)
    QWidget.__init__(self,parent,name,fl)
    if not name: self.setName("pyPetriDishCtrl")

    self.resize(QSize(202,202).expandedTo(self.minimumSizeHint()))
    self.clearWState(Qt.WState_Polished)

  def construct(self, session_mdl):
    self.m_session_mdl = session_mdl
    self.m_avida = None

    self.m_canvas = None
    self.m_cell_info = None
    self.m_petri_dish_layout = QVBoxLayout(self,0,0,"m_petri_dish_layout")
    self.m_petri_dish_layout.setResizeMode(QLayout.Minimum)
    self.m_canvas_view = pyPetriCanvasView(None, self,"m_canvas_view")
    self.m_petri_dish_layout.addWidget(self.m_canvas_view)
    self.m_changed_cell_items = []
    self.m_indexer = None
    self.m_color_lookup_functor = None
    self.m_background_rect = None
    self.m_change_list = None
    self.m_occupied_cells_ids = []

    self.m_target_dish_width = 270
    self.m_target_dish_scaling = 5.
    self.m_map_cell_width = 5

    self.connect( self.m_session_mdl.m_session_mdtr, PYSIGNAL("setAvidaSig"), self.setAvidaSlot)
    self.connect( self.m_canvas_view, PYSIGNAL("orgClickedOnSig"), self.m_session_mdl.m_session_mdtr, PYSIGNAL("orgClickedOnSig"))

  def setColorLookupFunctor(self, color_lookup_functor):
    self.m_color_lookup_functor = color_lookup_functor

  def createNewCellItem(self, n):
    self.m_occupied_cells_ids.append(n)
    return pyPopulationCellItem(
      self.m_avida.m_population.GetCell(n),
      (n%self.m_world_w) * self.m_map_cell_width,
      (n/self.m_world_w) * self.m_map_cell_width,
      self.m_map_cell_width,
      self.m_map_cell_width,
      self.m_canvas)

  def setAvidaSlot(self, avida):
    old_avida = self.m_avida
    self.m_avida = avida
    if(old_avida):
      del old_avida
    if(self.m_avida):
      pass

    self.m_change_list = self.m_avida.m_avida_threaded_driver.GetChangeList()

    self.m_world_w = cConfig.GetWorldX()
    self.m_world_h = cConfig.GetWorldY()
    self.m_initial_target_zoom = int(self.m_target_dish_width / self.m_world_w)
    print "self.m_map_cell_width", self.m_map_cell_width
    
    self.emit(PYSIGNAL("zoomSig"), (self.m_initial_target_zoom,))

    if self.m_canvas: del self.m_canvas
    self.m_canvas = QCanvas(self.m_map_cell_width * self.m_world_w, self.m_map_cell_width * self.m_world_h)
    self.m_canvas.setBackgroundColor(Qt.darkGray)
    self.m_canvas_view.setCanvas(self.m_canvas)
    if self.m_background_rect: del self.m_background_rect
    self.m_background_rect = QCanvasRectangle(
      0, 0,
      self.m_map_cell_width * self.m_world_w,
      self.m_map_cell_width * self.m_world_h,
      self.m_canvas)
    self.m_background_rect.setBrush(QBrush(Qt.black))
    self.m_background_rect.setPen(QPen(Qt.black))
    self.m_background_rect.show()
    self.m_background_rect.setZ(0.0)

    if self.m_cell_info: del self.m_cell_info
    self.m_cell_info = [None] * self.m_world_w * self.m_world_h
    self.m_occupied_cells_ids = []

    self.m_thread_work_cell_item_index = 0
    self.m_cs_min_value = 0
    self.m_cs_value_range = 0
    self.m_changed_cell_items = self.m_cell_info[:]
    self.updateCellItems(True)

  def setRange(self, min, max):
    self.m_cs_min_value = min
    self.m_cs_value_range = max - min

  def setIndexer(self, indexer):
    self.m_indexer = indexer

  def updateCellItem(self, cell_id):
    if self.m_cell_info[cell_id] is None:
      self.m_cell_info[cell_id] = self.createNewCellItem(cell_id)
    cell_info_item = self.m_cell_info[cell_id]
    self.m_indexer(cell_info_item, self.m_cs_min_value, self.m_cs_value_range)
    cell_info_item.updateColorUsingFunctor(self.m_color_lookup_functor)

  def updateCellItems(self, should_update_all = False):
    if self.m_cell_info:

      self.m_avida and self.m_avida.m_avida_threaded_driver.m_lock.acquire()
      if self.m_change_list:
        for index in range(self.m_change_list.GetChangeCount()):
          self.updateCellItem(self.m_change_list[index])
        self.m_change_list.Reset()
      self.m_avida and self.m_avida.m_avida_threaded_driver.m_lock.release()

      if should_update_all:
        for cell_id in self.m_occupied_cells_ids:
          self.updateCellItem(cell_id)

      if self.m_canvas: self.m_canvas.update()

  def extractPopulationSlot(self):
    population_dict = {}
    for x in range(self.m_world_w):
      for y in range(self.m_world_h):
        if self.m_avida != None:
          cell = self.m_avida.m_population.GetCell(x + self.m_world_w*y)
          if cell.IsOccupied() == True:
            organism = cell.GetOrganism()
            genome = organism.GetGenome()
            population_dict[cell.GetID()] = str(genome.AsString())
    self.emit(PYSIGNAL("freezeDishPhaseIISig"), (population_dict, ))

  def zoomSlot(self, zoom_factor):
    if self.m_canvas_view:
      m = QWMatrix()
      m.scale(zoom_factor/self.m_target_dish_scaling, zoom_factor/self.m_target_dish_scaling)
      self.m_canvas_view.setWorldMatrix(m)

