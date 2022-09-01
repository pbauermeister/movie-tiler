#!/usr/bin/python3
# (C) 2022 by Pascal Bauermeister <pascal.bauermeister@gmail.com>

"""Compose (as tiles) multiple movies into a new one."""

import cv2
import os.path
import sys

from argparse import ArgumentParser


def parse_geometry(s):
    parts = s.split('x')
    try:
        w, h = [int(v) for v in parts]
    except ValueError:
        print(f'Error: invalid dimension \'{s}\'; '
              f'expected syntax: INTEGERxINTEGER',
              file=sys.stderr)
        sys.exit(1)
    return w, h


def parse_args():
    parser = ArgumentParser(description=__doc__.strip())

    parser.add_argument('--resize', '-r', metavar='WIDTHxHEIGHT',
                        required=True,
                        help='resize each movie to this size in pixels')
    parser.add_argument('--grid', '-g', metavar='WIDTHxHEIGHT',
                        required=True,
                        help='grid size; need WIDTHxHEIGHT input movies')
    parser.add_argument('--fps', '-f', default=60,
                        help='resulting FPS')
    parser.add_argument('--every', '-e', default=1, type=int, metavar='N',
                        help='take only every Nth frame')
    parser.add_argument('--output', '-o', metavar='MOVIE_PATH.mp4',
                        help='optional output movie')
    parser.add_argument('--preview', '-p', action='store_true',
                        help='optionally show result in a graphical window')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='suppress progress output')
    parser.add_argument('input', metavar='MOVIE_PATH',
                        nargs='+',
                        help='input movies')
    args = parser.parse_args()

    # parse geometries
    args.resize = parse_geometry(args.resize)
    args.grid = parse_geometry(args.grid)

    # check consistency
    nb = args.grid[0] * args.grid[1]
    if len(args.input) != nb:
        details = f'{args.grid[0]}x{args.grid[1]}'
        print(f'Error: you need to specify {nb} (={details}) input movies',
              file= sys.stderr)
        sys.exit(1)

    return args


def get_frame_iterator(filePath, dim):
    ended = False
    last_frame = None
    cap = cv2.VideoCapture(filePath)
    while True:
        if ended:
            # repeat last frame
            yield last_frame, ended
            continue

        ret_val, frame = cap.read()
        if not ret_val:
            # last frame reached
            ended = True
            yield last_frame, ended
            continue

        # process frame
        frame = cv2.resize(frame, dim) #, interpolation=cv2.INTER_LANCZOS4)
        yield frame, ended
        last_frame = frame


def run(args):
    paths = args.input
    resize = args.resize
    cols, rows = args.grid

    if args.output:
        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        writer = cv2.VideoWriter(args.output, fourcc, args.fps,
                                 (resize[0]*cols, resize[1]*rows))

    if args.preview:
        window_name = 'Movie Tiler'
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        frame_delay = int(1000. / args.fps +.5) or 1

    iters = [get_frame_iterator(path, resize) for path in paths]
    finished = False
    endeds = {}
    nb_frames = 0

    while True:
        ix = 0
        bands = []
        do_it = (nb_frames % args.every) == 0

        for row in range(rows):
            this_row = []
            for col in range(cols):
                frame, ended = next(iters[ix])
                if ended:
                    endeds[ix] = True
                else:
                    endeds[ix] = False
                this_row.append(frame)
                ix += 1
            bands.append(cv2.hconcat(this_row))
        img = cv2.vconcat(bands)

        if args.preview and do_it:
            cv2.imshow(window_name, img)
            try:
                if cv2.waitKey(frame_delay) == 27:  # ESC key
                    break
                if cv2.getWindowProperty(window_name, 0) == -1:  # closed
                    break
            except cv2.error:
                break

        if args.output and do_it:
            writer.write(img)


        if endeds.values() and all(endeds.values()):
            finished = True
            break

        nb_frames += 1
        if not args.quiet:
            print(f'Frames: {nb_frames}', end='\r')

    if not args.quiet:
        print()

    if args.output:
        writer.release()
        print('Generated output:', args.output)
        if not finished:
            print(f'Output generation interrupted', file= sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    args = parse_args()
    run(args)
