#!/usr/bin/env python

from fingerprint import Fingerprint_Type, Fingerprint, Feature_Lists
from enum import Enum


class Table_Base():
  def __init__(self):
    self.print_table = None
    self.summary = None
    self.print_summary = None
    self.latex_summary = None

  def run(self, cursor, table_name, extra_selector=""):
    pass

  def __print_summary(self):
    pass

  def __latex_summary(self):
    pass

  def __str__(self):
    __str = ""
    for row in self.print_table:
      __str += ("{:<30}"*len(row)).format(*row) + "\n"

    if self.print_summary is not None:
      __str += self.print_summary

    return __str

  def __latex_helper(self):
    latex = ""
    for i, row in enumerate(self.print_table):
      if i is 0:
        header = "\\begin{tabular}{|l||"
        for _ in range(len(row)):
          header += "l|"
        header += "}\hline"
        latex += "{}\n".format(header)
        latex += "{} {}\n".format(" & ".join(row), "\\\\ \hline \hline")
      else:
        latex += "{} {}\n".format(" & " * (len(row) - 1), "\\\\[-7pt]")
        latex += "{} {}\n".format(" & ".join(row).replace('%', '\%'), "\\\\ \hline")

    latex += "\\end{tabular}\n"
    latex += "\\vspace{0.05in}\n\n"

    if self.latex_summary is not None:
      latex += self.latex_summary

    return latex

  def __format__(self, code):
    if code == "latex":
      return self.__latex_helper()
    else:
      return format(str(self), code)


class Cross_Table(Table_Base):
  def __init__(self, feat_list, browsers):
    Table_Base.__init__(self)
    self.feat_list, self.browsers = feat_list, browsers

  def __cross_helper(self, b1, b2, cursor, table_name, attrs, extra_selector):
    cursor.execute("SELECT user_id FROM {} WHERE browser='{}' {}".format(table_name, b1, extra_selector))
    tuids = [uid for uid, in cursor.fetchall()]

    uids = []
    for uid in tuids:
      cursor.execute("SELECT user_id FROM {} WHERE user_id='{}' AND browser='{}' {}".format(table_name, uid, b2, extra_selector))
      for uid, in cursor.fetchall():
        uids.append(uid)

    if len(uids) is 0:
        return None

    fp_to_count = {}
    num_cross_browser = 0.0

    for uid in uids:
      cursor.execute("SELECT image_id FROM {} WHERE browser='{}' AND user_id='{}'".format(table_name, b1, uid))
      image1_id = cursor.fetchone()[0]

      cursor.execute("SELECT image_id FROM {} WHERE browser='{}' AND user_id='{}'".format(table_name, b2, uid))
      image2_id = cursor.fetchone()[0]

      fp_1 = Fingerprint(cursor, image1_id, table_name, Fingerprint_Type.CROSS, attrs, b2)
      fp_2 = Fingerprint(cursor, image2_id, table_name, Fingerprint_Type.CROSS, attrs, b1)

      if fp_1 == fp_2:
        num_cross_browser += 1
        if fp_1 in fp_to_count:
          fp_to_count[fp_1] += 1
        else:
          fp_to_count.update(
            {
              fp_1: 1
            }
          )

    num_distinct = max(float(len(fp_to_count)), 1.0)
    num_unique = 0.0
    for _, count in fp_to_count.items():
      if count == 1:
        num_unique += 1.0

    num_uids = max(float(len(uids)), 1.0)

    return int(num_uids), num_cross_browser/num_uids, num_unique/num_cross_browser

  def __print_summary(self):
    __str = ""

    if self.summary is not None:
      __str += "Summary: {:3.2f}%CB  {:3.2f}%Uni\n".format(self.summary[0]*100.0, self.summary[1]*100.0)
      __str += "Average Identifable: {:3.2f}%Iden".format(self.summary[0]*self.summary[1]*100.0)

    return __str

  def __latex_summary(self):
    latex = "\LARGE\n"
    if self.summary is not None:
      latex += "Summary: ${:3.2f}$\%CB  ${:3.2f}$\%Uni\n\n".format(self.summary[0]*100.0, self.summary[1]*100.0)
      latex += "Average Identifable: ${:3.2f}$\%Iden\n\n".format(self.summary[0]*self.summary[1]*100)
    return latex

  def run(self, cursor, table_name, extra_selector=""):
    self.res_table = {}
    for i in range(len(self.browsers)):
      for j in range(i + 1, len(self.browsers)):
        b1, b2 = self.browsers[i], self.browsers[j]
        self.res_table.update(
          {
            (b1, b2): self.__cross_helper(b1, b2, cursor, table_name, self.feat_list, extra_selector)
          }
        )

    for i in range(len(self.browsers)):
      for j in range(0, i):
        b1, b2 = self.browsers[i], self.browsers[j]
        self.res_table.update(
          {
            (b1, b2): self.res_table[(b2, b1)]
          }
        )
    self.print_table = []
    self.print_table.append(["Browser"] + self.browsers)
    for b1 in self.browsers:
      row = [b1]
      for b2 in self.browsers:
        try:
          num, cb, u = self.res_table[(b1, b2)]
          row.append("{:3d} {:3.1f}%CB  {:3.1f}%Uni {:3.1f}".format(num, cb*100.0, u*100.0, cb*u*100.0))
        except:
          row.append("")
      self.print_table.append(row)

    ave_cb, ave_u, sum_weights = 0.0, 0.0, 0.0
    for _, val in self.res_table.items():
      try:
        count, cb, u = val
      except:
        continue

      sum_weights += float(count)
      ave_cb += float(cb)*float(count)
      ave_u += float(u)*float(count)

    self.summary = ave_cb/sum_weights, ave_u/sum_weights
    self.print_summary = self.__print_summary()
    self.latex_summary = self.__latex_summary()

class Single_Table(Table_Base):
  def __init__(self, feat_list, browsers):
    Table_Base.__init__(self)
    self.feat_list, self.browsers = feat_list, browsers

  def __single_helper(self, b, cursor, table_name, attrs, extra_selector):
    cursor.execute("SELECT image_id FROM {} WHERE browser='{}' {}".format(table_name, b, extra_selector))
    image_ids = [uid for uid, in cursor.fetchall()]

    if len(image_ids) is 0:
      return None

    fp_to_count = {}
    for uid in image_ids:
      fp = Fingerprint(cursor, uid, table_name, Fingerprint_Type.SINGLE, attrs)
      if fp in fp_to_count:
        fp_to_count[fp] += 1
      else:
        fp_to_count.update(
          {
            fp : 1
          }
        )

    num_distinct = max(float(len(fp_to_count)), 1.0)
    num_unique = 0.0
    for _, count in fp_to_count.items():
      if count == 1:
        num_unique += 1.0
    num_uids = len(image_ids)

    return int(num_uids), num_unique/num_uids

  def __print_summary(self):
    __str = ""
    if self.summary is not None:
      __str += "Summary: {:3.2f}%Iden\n".format(self.summary*100.0)
    return __str

  def __latex_summary(self):
    latex = "\LARGE\n"
    if self.summary is not None:
      latex += "Average Identifable: ${:3.2f}$\%Iden\n".format(self.summary*100)
    return latex

  def run(self, cursor, table_name, extra_selector=""):
    self.res_table = {}
    for b in self.browsers:
      self.res_table.update(
        {
          b : self.__single_helper(b, cursor, table_name, self.feat_list, extra_selector)
        }
      )

    self.print_table = []
    self.print_table.append(["Browser"] + self.browsers)
    row = ["Single"]
    for b in self.browsers:
      try:
        _, u = self.res_table[b]
        row.append("{:3.1f}%Iden".format(u*100.0))
      except:
        row.append("")
    self.print_table.append(row)

    ave_u, sum_weights = 0.0, 0.0
    for _, val in self.res_table.items():
      try:
        count, u = val
      except:
        continue

      sum_weights += count
      ave_u += u*count

    self.summary = ave_u/sum_weights
    self.print_summary = self.__print_summary()
    self.latex_summary = self.__latex_summary()

class Results_Table():
  def factory(fp_type, feat_list, browsers):
    if fp_type == Fingerprint_Type.CROSS:
      return Cross_Table(feat_list, browsers)
    elif fp_type == Fingerprint_Type.SINGLE:
      return Single_Table(feat_list, browsers)
    else:
      RuntimeError("Type not supported!")
  factory = staticmethod(factory)


class Feature_Table(Table_Base):
  def __init__(self, browsers):
    Table_Base.__init__(self)
    self.browsers = browsers

  def __helper(self, cursor, table_name, feature, extra_selector=""):
    cb = Results_Table.factory(Fingerprint_Type.CROSS, feature, self.browsers)
    cb.run(cursor, table_name)
    s = Results_Table.factory(Fingerprint_Type.SINGLE, feature, self.browsers)
    s.run(cursor, table_name)

    return (s.summary,) + cb.summary

  def run(self, cursor, table_name, extra_selector=""):
    self.res_table = []
    for feat in Feature_Lists.All:
      self.res_table.append(self.__helper(cursor, table_name, feat, extra_selector))

    self.print_table = [["Feature", "Single-browser", "Cross-browser"]]
    for i in range(len(self.res_table)):
      feat = Feature_Lists.All[i]
      su, cb, cbu = self.res_table[i]
      self.print_table.append([Feature_Lists.Mapped_All[i], "{:3.1f}%Iden".format(su*100), "{:3.1f}%Iden={:3.1f}%CB*{:3.1f}%Uni".format(cb*cbu*100.0,cb*100,cbu*100)])



class VAL(Enum):
  EQ = 0
  LT = 1
  GT = 2


class Cross_Diff_Table(Table_Base):
  def __init__(self, feat_list_A, feat_list_B, browsers):
    Table_Base.__init__(self)
    self.feat_list_A, self. feat_list_B, self.browsers = feat_list_A,  feat_list_B, browsers

  def __type_helper(self, a, b):
    t = None
    if a == b:
      t = VAL.EQ
    elif a < b:
      t = VAL.LT
    else:
      t = VAL.GT

    return a, t

  def run(self, cursor, table_name, extra_selector=""):
    self.table_A = Results_Table.factory(Fingerprint_Type.CROSS, self.feat_list_A, self.browsers)
    self.table_A.run(cursor, table_name, extra_selector)

    table_B = Results_Table.factory(Fingerprint_Type.CROSS, self.feat_list_B, self.browsers)
    table_B.run(cursor, table_name, extra_selector)

    self.res_table = {}
    for key, A in self.table_A.res_table.items():
      if A is not None:
        B = table_B.res_table[key]
        e = []
        for i in range(len(A)):
          e.append(self.__type_helper(A[i], B[i]))

        self.res_table.update(
          {
            key : e
          }
        )

    acb, au = self.table_A.summary
    bcb, bu = table_B.summary
    ai = acb*au
    bi = bcb*bu
    cb_out = self.__frmt_helper("{:3.2f}%CB".format(acb*100.0), self.__type_helper(acb, bcb))
    u_out = self.__frmt_helper("{:3.2f}%Uni".format(au*100.0), self.__type_helper(au, bu))
    i_out = self.__frmt_helper("{:3.2f}%Iden".format(ai*100.0), self.__type_helper(ai, bi))

    self.frmt_summary = ["Summary: {} {}".format(cb_out, u_out)]
    self.frmt_summary.append("Average Identifiable: {}".format(i_out))


  def __str__(self):
    self.summary = self.table_A.summary
    self.print_table = self.table_A.print_table
    return Table_Base.__str__(self)

  def __frmt_helper(self, val, t):
    if t == VAL.EQ:
      return val
    elif t == VAL.LT:
      return "{\\color{blue} " + str(val) + "$\\downarrow$}"
    else:
      return "{\\color{red} " + str(val) + "$\\uparrow$}"

  def __latex_helper(self):
    self.print_table = []
    self.print_table.append(["Browser"] + self.browsers)

    for b1 in self.browsers:
      row = [b1]
      for b2 in self.browsers:
        if (b1, b2) in self.res_table:
            _, cb, u = self.res_table[(b1, b2)]
            val, t = cb
            out = self.__frmt_helper("{:3.1f}%CB".format(val*100), t) + " "
            val, t = u
            out += self.__frmt_helper("{:3.1f}%Uni".format(val*100), t)
            row.append(out)
        else:
          row.append("")
      self.print_table.append(row)

  def __format__(self, code):
    if code == "latex":
      self.__latex_helper()
      self.summary = None
      __str = Table_Base.__format__(self, code)

      __str += "\n\LARGE\n"
      for e in self.frmt_summary:
        __str += "{}\n\n".format(e.replace("%", "\%"))

      __str += "{\color{red} red} values have increased\n\n"
      __str += "{\color {blue} blue} values have decreased\n\n"
      return __str
    else:
      return format(str(self), code)


class Single_Diff_Table(Table_Base):
  def __init__(self, feat_list_A,  feat_list_B, browsers):
    Table_Base.__init__(self)
    self.feat_list_A, self. feat_list_B, self.browsers = feat_list_A,  feat_list_B, browsers


  def __type_helper(self, a, b):
    t = None
    if a == b:
      t = VAL.EQ
    elif a < b:
      t = VAL.LT
    else:
      t = VAL.GT

    return a, t

  def run(self, cursor, table_name, extra_selector=""):
    self.table_A = Results_Table.factory(Fingerprint_Type.SINGLE, self.feat_list_A, self.browsers)
    self.table_A.run(cursor, table_name, extra_selector)

    table_B = Results_Table.factory(Fingerprint_Type.SINGLE, self.feat_list_B, self.browsers)
    table_B.run(cursor, table_name, extra_selector)

    self.res_table = {}
    for key, A in self.table_A.res_table.items():
      if A is not None:
        B = table_B.res_table[key]
        e = []
        for i in range(len(A)):
          e.append(self.__type_helper(A[i], B[i]))

        self.res_table.update(
          {
            key : e
          }
        )

    au = self.table_A.summary
    bu = table_B.summary
    i_out = self.__frmt_helper("{:3.2f}%Iden".format(au*100.0), self.__type_helper(au, bu))
    self.frmt_summary = ["Average Identifiable: {}".format(i_out)]


  def __str__(self):
    self.summary = self.table_A.summary
    self.print_table = self.table_A.print_table
    return Table_Base.__str__(self)

  def __frmt_helper(self, val, t):
    if t == VAL.EQ:
      return val
    elif t == VAL.LT:
      return "{\\color{blue} " + str(val) + "$\\downarrow$}"
    else:
      return "{\\color{red} " + str(val) + "$\\uparrow$}"

  def __latex_helper(self):
    self.print_table = []
    self.print_table.append(["Browser"] + self.browsers)
    row = ["Single"]
    for b in self.browsers:
      if b in self.res_table:
        _, u = self.res_table[b]
        val, t = u
        out = self.__frmt_helper("{:3.1f}%Iden".format(val*100), t)
        row.append(out)
      else:
        row.append("")

    self.print_table.append(row)


  def __format__(self, code):
    if code == "latex":
      self.__latex_helper()
      self.summary = None
      __str = Table_Base.__format__(self, code)
      __str += "\n\LARGE\n"
      for e in self.frmt_summary:
        __str += "{}\n\n".format(e.replace("%", "\%"))

      __str += "{\color{red} red} values have increased\n\n"
      __str += "{\color {blue} blue} values have decreased\n\n"
      return __str
    else:
      return format(str(self), code)


class Diff_Table():
  def factory(fp_type, feat_list_A,  feat_list_B, browsers):
    if fp_type == Fingerprint_Type.CROSS:
      return Cross_Diff_Table(feat_list_A, feat_list_B, browsers)
    elif fp_type == Fingerprint_Type.SINGLE:
      return Single_Diff_Table(feat_list_A, feat_list_B, browsers)
    else:
      RuntimeError("Type not supported!")
  factory = staticmethod(factory)

class Summary_Table(Table_Base):
  def __init__(self, browsers):
    Table_Base.__init__(self)
    self.browsers = browsers

  def run(self, cursor, table_name):

    self.print_table = []
    self.print_table.append(["Type", "amiunique.org", "Our's"])
    row = ["Cross Browser"]

    ami = Results_Table.factory(Fingerprint_Type.CROSS, Feature_Lists.CB_Amiunique, self.browsers)
    ami.run(cursor, table_name)

    ours = Results_Table.factory(Fingerprint_Type.CROSS, Feature_Lists.Cross_Browser, self.browsers)
    ours.run(cursor, table_name)

    summary = ami.summary
    row.append("{:3.2f}%Iden".format(summary[0]*summary[1]*100.0))
    summary = ours.summary
    row.append("{:3.2f}%Iden".format(summary[0]*summary[1]*100.0))
    self.print_table.append(row)

    row = ["Single Browser"]

    ami = Results_Table.factory(Fingerprint_Type.SINGLE, Feature_Lists.Amiunique, self.browsers)
    ami.run(cursor, table_name)

    ours = Results_Table.factory(Fingerprint_Type.SINGLE, Feature_Lists.Single_Browser, self.browsers)
    ours.run(cursor, table_name)

    summary = ami.summary
    row.append("{:3.2f}%Iden".format(summary*100.0))
    summary = ours.summary
    row.append("{:3.2f}%Iden".format(summary*100.0))
    self.print_table.append(row)
