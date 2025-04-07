import os
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import pydicom
from rt_utils import RTStructBuilder
from PIL import Image, ImageOps
import matplotlib.pyplot as plt


class ImageToRTStructGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Powerstruct")

        # Image file picker
        tk.Label(root, text="Select Image:").grid(row=0, column=0, sticky="w")
        self.image_path = tk.Entry(root, width=40)
        self.image_path.grid(row=0, column=1)
        tk.Button(root, text="Browse", command=self.select_image).grid(row=0, column=2)

        # Posterized dose levels
        tk.Label(root, text="# Dose Levels:").grid(row=1, column=0, sticky="w")
        self.dose_levels = tk.Entry(root, width=10)
        self.dose_levels.grid(row=1, column=1)

        # Dimensions
        tk.Label(root, text="Image width along sagittal axis (cm):").grid(row=2, column=0, sticky="w")
        self.sag_width = tk.Entry(root, width=10)
        self.sag_width.grid(row=2, column=1)
        
        tk.Label(root, text="Image height along axial axis (cm):").grid(row=3, column=0, sticky="w")
        self.ax_height = tk.Entry(root, width=10)
        self.ax_height.grid(row=3, column=1)
        
        tk.Label(root, text="Image thickness along coronal axis (cm):").grid(row=4, column=0, sticky="w")
        self.cor_thick = tk.Entry(root, width=10)
        self.cor_thick.grid(row=4, column=1)

        # DICOM Folder Picker
        tk.Label(root, text="CT DICOM Folder:").grid(row=5, column=0, sticky="w")
        self.dicom_path = tk.Entry(root, width=40)
        self.dicom_path.grid(row=5, column=1)
        tk.Button(root, text="Browse", command=self.select_dicom_folder).grid(row=5, column=2)

        # Output Folder Picker
        tk.Label(root, text="Output Folder:").grid(row=6, column=0, sticky="w")
        self.output_path = tk.Entry(root, width=40)
        self.output_path.grid(row=6, column=1)
        tk.Button(root, text="Browse", command=self.select_output_folder).grid(row=6, column=2)
        
        # Preview Masks checkbox
        self.preview_masks = tk.BooleanVar()
        tk.Checkbutton(root, text="Preview Masks?", variable=self.preview_masks).grid(row=7, column=0, sticky="w")

        # Run button
        self.run_button = tk.Button(root, text="Run", command=self.run_script)
        self.run_button.grid(row=7, column=1, pady=10)

        # Help button
        self.help_button = tk.Button(root, text="Help", command=self.help_popup)
        self.help_button.grid(row=7, column=2, pady=10)

        # Status label
        self.status_label = tk.Label(root, text="", fg="green")
        self.status_label.grid(row=8, column=1, pady=5)

        # Console output box
        self.console = tk.Text(root, height=10, width=80, state="disabled", bg="black", fg="white")
        self.console.grid(row=9, column=0, columnspan=3, padx=10, pady=10)

        # Redirect stdout
        self.original_stdout = os.sys.stdout
        os.sys.stdout = StdoutRedirector(self.console)
        print("Welcome to 9-k's Powerstruct, a GUI wrapper for Qurit's rt-utils!")
        
        # Redirect stderr
        self.original_stderr = os.sys.stderr
        os.sys.stderr = StdoutRedirector(self.console)


    def select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.tif;*.bmp")])
        if file_path:
            self.image_path.delete(0, tk.END)
            self.image_path.insert(0, file_path)

    def select_dicom_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.dicom_path.delete(0, tk.END)
            self.dicom_path.insert(0, folder_path)

    def select_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_path.delete(0, tk.END)
            self.output_path.insert(0, folder_path)

    def run_script(self):
        if (not bool(self.image_path.get().strip()) or 
            not bool(self.dose_levels.get().strip()) or 
            not bool(self.sag_width.get().strip()) or
            not bool(self.ax_height.get().strip()) or 
            not bool(self.cor_thick.get().strip()) or 
            not bool(self.output_path.get().strip()) or 
            not bool(self.dicom_path.get().strip())):
            messagebox.showerror("Error", "You're missing something. Make sure all the fields are populated.")
            return
        self.status_label.config(text="Processing...", fg="blue")
        self.root.update()
        main(self)
        self.status_label.config(text="Completed!", fg="green")
        messagebox.showinfo("Process Complete", "RTSTRUCT file has been generated successfully.")
        
    def help_popup(self):
        helpmsg1 = ""
        helpmsg1 += "1. First, a phantom CT dataset is needed. "
        helpmsg1 += "I have not seen if real CT datasets work - only tested with "
        helpmsg1 += "the phantom generating method in Eclipse's Contouring workspace.\n\n"
        helpmsg1 += "2. Export the CT dataset from a dummy patient that will be used to house the phantom, structs, and plans. "
        helpmsg1 += "Make sure your phantom is the correct shape and HFS orientation! "
        helpmsg1 += "I recommend using a high-resolution phantom. 0.5mm slice thickness works well.\n\n"
        helpmsg1 += "3. Next, choose an image you want to print. This can be in color, or be black and white. Most any format will work. "
        helpmsg1 += "Works in Varian's ARIA - untested for other OISs."
        
        helpmsg2 = ""
        helpmsg2 += "Select Image: Press Browse, then select the image you want to turn into rtstructs.\n\n"
        helpmsg2 += "Dose Levels: The image is converted to black and white, then into the specified number of dose levels. "
        helpmsg2 += "Each of these dose levels will end up as an individual RT Structure in your TPS. "
        helpmsg2 += "Though they are labelled with darkness levels, you can choose whatever doses you want for the individual dose levels. "
        helpmsg2 += "Usually 6-8 masks is a good place to start. If your masks are too noisy upon import, "
        helpmsg2 += "consider blurring your image before import.\n\n"
        helpmsg2 += "Image dimensions are obvious - choose the size you want. Note that the dimensions should agree "
        helpmsg2 += "with the aspect ratio of your image, or you can end up distorting your image. "
        helpmsg2 += "For thickness, usually 1 cm works fine.\n\n"
        helpmsg2 += "CT DICOM Folder: select the folder containing your phantom CT DICOM images.\n\n"
        helpmsg2 += "Output Folder: select where you want the output rtstruct file, titled powerstructs.dcm, to go.\n\n"
        helpmsg2 += "Selecting 'Preview Masks?' will open each mask in a popup window and is slow. Usually, leave this off.\n\n"
        helpmsg2 += "I shouldn't have to tell you what 'Run' does.\n\n"
        helpmsg2 += "Please be patient after running - the code is slow."

        helpmsg3 = ""
        helpmsg3 += "1. Take your powerstructs.dcm file and import it into your TPN. "
        helpmsg3 += "PLEASE note - too many dose levels (e.g. 20) on too high resolution of a phantom (0.1mm slices) could cause "
        helpmsg3 += "the import to take a long time, or even hang or crash. Your OIS isn't a miracle worker. "
        helpmsg3 += "Warnings on import is normal, failures are not.\n\n"
        helpmsg3 += "2. For Aria, after importing the RTStructs, to get the structure set "
        helpmsg3 += "back into the original phantom CT, not just a co-registered CT, "
        helpmsg3 += "navigate to Contouring, open the dummy patient, double click on the orange dotted line "
        helpmsg3 += "surrounding the original phantom CT and the new dummy CT, called RTStruct# or something similar. "
        helpmsg3 += "Right click on the structure set under RTStruct#, also confusingly called 'RTstruct', "
        helpmsg3 += "and select 'Copy Structures to Registered Image. Don't copy over the BODY - keep the phantom's BODY."
        
        helpmsg4 = ""
        helpmsg4 += "If you're wondering why the contours are that color, I tried to make it match the colors of\n"
        helpmsg4 += "exposed and unexposed radiochromic film. Didn't work out amazing, but it works.\n\n"
        helpmsg4 += "Create a plan. I've gotten best results with many beams, all at gantry 0, but with progressively "
        helpmsg4 += "rotated collimators (so collimator 0, 15, 30, 45... etc.). "
        helpmsg4 += "I'm sure other great ways exist - experiment!\n\n"
        helpmsg4 += "Head into your optimizer, and set an upper and lower objective for each target level contour. "
        helpmsg4 += "For simplicity, I set the dose levels to match the '####' in the '#### Dark' contour names. "
        helpmsg4 += "I set identical priority for everything, and optimization is very quick.\n\n"
        helpmsg4 += "Usually, clearer image results, at the expense of higher MU, are found with sliding window delivery. "
        helpmsg4 += "Conversely, static fields use less MU for a somewhat worse result.\n\n"
        helpmsg4 += "The necessary MUs can be decreased by decreasing SSD, to say 70 or so. "
        helpmsg4 += "This may also improve image quality due to reduced penumbra.\n\n"
        helpmsg4 += "Export the plans as a file and deliver to your film!\n\n"
        helpmsg4 += "Please utilize your best judgement before delivering a plan."

        helpmsg5 = ""
        helpmsg5 += "Using Tkinter, numpy, pydicom, Pillow, and matplotlib.\n\n"
        helpmsg5 += "This would not be possible without Qurit's RT-Utils! Paper here: https://doi.org/10.21105/joss.07361 "
        helpmsg5 += "and code here: https://github.com/qurit/rt-utils\n\n"
        helpmsg5 += "Source for this project (there's not much - it's literally a single .py file!) can be found at "
        helpmsg5 += "https://github.com/9-k/Powerstruct. "
        helpmsg5 += "Don't laugh - I'm a physicist, not a programmer.\n\n"
        helpmsg5 += "And if you're wondering, the name comes from 'image to rtstruct' -> 'i2r', and since "
        helpmsg5 += "Power = I^2R, Powerstruct was born!"
        
        messagebox.showinfo("Before Using Powerstruct", helpmsg1)
        messagebox.showinfo("Using Powerstruct", helpmsg2)
        messagebox.showinfo("Importing Tips", helpmsg3)
        messagebox.showinfo("Planning Tips", helpmsg4)
        messagebox.showinfo("Attributions", helpmsg5)
        messagebox.showinfo("License",
"""MIT License

Copyright (c) 2025 9-k

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.""")

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", message)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


def load_dicom_slices(folder_path):
    """Loads all DICOM slices in a folder, sorts them by axial position."""
    slices = []
    for file in os.listdir(folder_path):
        filepath = os.path.join(folder_path, file)
        try:
            ds = pydicom.dcmread(filepath, force=True)
            if hasattr(ds, "ImagePositionPatient"):
                slices.append(ds)
        except:
            continue  # Skip non-DICOM files
    slices.sort(key=lambda ds: ds.ImagePositionPatient[2])
    return slices

def create_3d_masks(image_path, phantom_folder_path, output_folder_path, wanted_image_dims_sag_ax_cor_cm, num_levels, preview_masks):
    slices = load_dicom_slices(phantom_folder_path)
    if not slices:
        raise ValueError("No valid DICOM slices found.")

    slice_thickness = slices[0].SliceThickness
    pixel_spacing = slices[0].PixelSpacing  # [coronal direction, sagittal direction], assuming HFS.
    orientation = slices[0].ImageOrientationPatient
    # I want it to be close to that, but within rounding errors.
    if np.linalg.norm(np.array(list(orientation))-np.array([1, 0, 0, 0, 1, 0])) > 0.1: 
        raise ValueError("Seems like CT isn't HFS - code needs a HFS scan?")
    # If the code makes it here, then it's the right orientation
    
    num_slices = len(slices) 
    rows, cols = slices[0].pixel_array.shape  

    # x is sagittal
    # y is coronal
    # z must be axial, according to the rtstructbuilder.

    shape = [cols, rows, num_slices]
    matrix = np.zeros(shape, dtype=bool)  # 3D boolean matrix (all False)
    
    wanted_sag_dim_cm = wanted_image_dims_sag_ax_cor_cm[0]
    wanted_ax_dim_cm = wanted_image_dims_sag_ax_cor_cm[1]
    wanted_cor_dim_cm = wanted_image_dims_sag_ax_cor_cm[2]
    
    wanted_sag_dim_px = int(wanted_sag_dim_cm*10/pixel_spacing[1])
    wanted_ax_dim_px = int(wanted_ax_dim_cm*10/slice_thickness)
    wanted_cor_dim_px = int(wanted_cor_dim_cm*10/pixel_spacing[0])
    
    image = Image.open(image_path).convert("L")
    resized_image = image.resize((wanted_sag_dim_px, wanted_ax_dim_px))

    two_d_masks = create_2d_masks_fitting_coronal_slice(resized_image, matrix[:,0,:], num_levels, preview_masks)
    three_d_masks = populate_3d_masks(two_d_masks, matrix, wanted_cor_dim_px)
    create_and_save_rtstructs_from_three_d_masks(three_d_masks, phantom_folder_path, output_folder_path)

def create_2d_masks_fitting_coronal_slice(image, coronal_slice, num_levels, preview_masks):
    image = ImageOps.flip(image)
    mask_canvas = Image.new("L", coronal_slice.shape, 255)
    paste_sag = (mask_canvas.width - image.width) // 2
    paste_ax  = (mask_canvas.height - image.height) // 2
    mask_canvas.paste(image, (paste_sag, paste_ax))
    img_array = np.array(mask_canvas).T
    thresholds = np.linspace(0, 255, num_levels+1)
    levels = [(lower, upper) for lower, upper in zip(thresholds[:-1], thresholds[1:])]
    two_d_masks = [((level[0] <= img_array) & (img_array < level[1])).astype(bool) for level in levels]
    if preview_masks:
        for two_d_mask in two_d_masks:
            plt.imshow(np.flip(two_d_mask.T, axis=0))
            plt.show()
    return two_d_masks

def populate_3d_masks(two_d_masks, empty_ct_np_matrix, wanted_cor_dim_px):
    three_d_masks = []
    for two_d_mask in two_d_masks:
        three_d_mask = np.zeros_like(empty_ct_np_matrix, dtype=bool)
        for i in range(wanted_cor_dim_px):
            three_d_mask[(three_d_mask.shape[0]//2)-i,:,:] = two_d_mask
        three_d_masks.append(three_d_mask)
    return three_d_masks

def create_and_save_rtstructs_from_three_d_masks(three_d_masks, phantom_folder_path, output_folder_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=phantom_folder_path)
    num_masks = len(three_d_masks)
    unshot_color = [165, 154, 89]
    shot_color = [62, 69, 58]
    for i, three_d_mask in enumerate(three_d_masks):
        lerp_param = ((num_masks-i)/num_masks)
        structure_name = f"{1000*lerp_param:.0f} Dark"
        if not three_d_mask.any():
            print(f"{structure_name} is an empty mask. Skipping:")
            continue
        lerp_color = [round((1 - lerp_param) * unshot_component + lerp_param * shot_component) for unshot_component, shot_component in zip(unshot_color, shot_color)]
        rtstruct.add_roi(mask=three_d_mask, 
                         color=lerp_color, 
                         name=structure_name,
                         description="Generated with 9-k's Powerstruct!",
                         approximate_contours=False # turning this true makes the files smaller but rtstructs weirder...
                         )
    rtstruct.save(os.path.join(output_folder_path, "powerstructs.dcm"))

def main(app):
    image_path = app.image_path.get()
    output_folder_path = app.output_path.get()
    phantom_folder_path = app.dicom_path.get()
    num_levels = int(app.dose_levels.get())
    
    wanted_image_dims_sag_ax_cor_cm = [
        float(app.sag_width.get()), 
        float(app.ax_height.get()), 
        float(app.cor_thick.get())
    ]
    
    create_3d_masks(image_path, phantom_folder_path, output_folder_path,
                    wanted_image_dims_sag_ax_cor_cm, num_levels, app.preview_masks.get())

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToRTStructGUI(root)
    root.mainloop()
