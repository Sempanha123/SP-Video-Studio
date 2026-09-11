import QtQuick 2.15

StatusBadge {
    property string compatibility: "unknown"
    text: {
        if (compatibility === "compatible") return "Compatible"
        if (compatibility === "compatible_with_warning") return "Limited"
        if (compatibility === "not_recommended") return "Not Recommended"
        return "Unknown"
    }
    status: {
        if (compatibility === "compatible") return "ready"
        if (compatibility === "compatible_with_warning") return "warning"
        if (compatibility === "not_recommended") return "repair-required"
        return "unknown"
    }
}
