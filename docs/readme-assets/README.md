# README image provenance

The SVG artwork illustrates the workflow. The six PNGs are user-supplied screenshots of ShadowVendor's responsive dashboard, supplied on 26 October 2026. They are copied byte-for-byte from those captures: no chart values, labels, colors, or geometry were redrawn. All six show the [48-address simulated VLAN example](../examples/vlan-review.txt), using the bundled vendor cache and the dashboard implementation at commit `994896e42fc1675af2f7ea709e5e81923274a57d`.

- `dashboard-summary.png`: 48 unique MAC addresses, five vendor labels, four known VLANs.
- `vendor-overview.png`: Cisco 14, Dell 12, VMware 10, Apple 8, Intel 4. Intel's table row lies below the visible scroll area; its slice is visible.
- `vlan-mac-counts.png`: VLAN totals 12, 8, 18, and 10; the hover shows VLAN 10 / 12.
- `vlan-vendor-labels.png`: vendor-label counts 3, 2, 4, and 2; the hover shows VLAN 30 / 4.
- `vlan-vendor-heatmap.png`: columns Cisco, Dell, VMware, Apple, Intel. The visible tooltip identifies Apple / VLAN 10 / 0; it extends over the neighboring Intel cell, whose value is 4.
- `vlan-vendor-stack.png`: the same counts grouped into vendor series, totaling 12, 8, 18, and 10. All five vendors fit the top-five limit in this example.

The former light-theme README chart captures have been removed. No browser automation was used to produce the replacement images.

## Data verification

The [accuracy tests](../../tests/test_dashboard_accuracy.py) independently specify the expected compositions and verify both CLI and API output, device CSV records, all chart and table values, metrics, and serialized hover data. Expected VLAN compositions:

- VLAN 10: Cisco 6, Dell 2, Intel 4.
- VLAN 20: Dell 6, Apple 2.
- VLAN 30: Cisco 4, Dell 4, VMware 4, Apple 6.
- VLAN 40: Cisco 4, VMware 6.

These are simulated records, not measurements of a production network. Percentages are rounded independently. Vendor labels reflect the bundled snapshot, not a fresh manufacturer attribution check.

## Reproduce

Follow the root README's installation and bundled-cache setup, then run:

```bash
python ShadowVendor.py --offline docs/examples/vlan-review.txt
```

Open `output/vendor_distribution.html` in a browser with access to the Plotly CDN. Each run replaces that HTML and the current summary. Browser size and zoom affect panel arrangement; a different vendor cache may change labels. The captures show the inspected sizes only, not proof of every viewport or interaction.
